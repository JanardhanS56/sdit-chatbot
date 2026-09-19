"""
RAG Pipeline — SDIT Tech-Bot
Handles: hybrid retrieval, fallback logic, and dynamic LLM calling.
"""

import json
import re
import logging
from typing import Optional
from supabase import create_client, Client
try:
    from .config import settings
except ImportError:
    from config import settings
from openai import AsyncOpenAI

logger = logging.getLogger("sdit-techbot.rag")

SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "at", "can", "do", "does", "for", "how",
    "i", "in", "is", "of", "on", "the", "to", "what", "when", "where",
    "which", "who", "with", "you", "your", "sdit",
}

# ──────────────────────────────────────────────
# Clients
# ──────────────────────────────────────────────
_supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

_llm_client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_api_base
)

_embedding_client = None
if settings.embedding_api_key and settings.embedding_api_base:
    _embedding_client = AsyncOpenAI(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_api_base,
    )

# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are SDIT Tech-Bot, the official AI campus assistant for Shree Devi Institute of Technology (SDIT), Mangaluru.

Your job is to help students, faculty, and visitors with accurate information about SDIT.

Rules you must always follow:
1. ONLY use information from the provided CONTEXT to answer questions about SDIT-specific facts (fees, dates, faculty names, hostel rules, placement stats, etc.).
2. If the CONTEXT does not contain enough information to answer, say: "I don't have verified information about that right now. Please contact the SDIT helpdesk at +91 9353619812 for accurate details."
3. Never invent or guess SDIT-specific information (fees, exam dates, faculty names, etc.).
4. For general guidance (resume writing, aptitude tips, study advice), you may use your general knowledge — but still be helpful and concise.
5. Distinguish clearly between what the CONTEXT confirms and what it does not. If the CONTEXT says a facility or activity is available, do not infer permission rules, registration, team membership, timings, or access conditions unless they are explicitly stated.
6. Always be friendly, warm, and approachable. You are talking to college students and visitors.
7. Keep answers concise for simple questions. Provide detail only when the question needs it.
8. If someone seems distressed or mentions an emergency, provide the SDIT helpdesk number immediately: +91 9353619812.
9. Do not expose internal system details, database structure, or API information.
10. If a question is completely unrelated to SDIT or general academic guidance, politely say it is outside your area and redirect to the helpdesk.

Your personality: Friendly, helpful, professional, knowledgeable about SDIT. Think of yourself as a helpful senior student who knows everything about the college.
"""

# ──────────────────────────────────────────────
# Step 1: Generate Embedding
# ──────────────────────────────────────────────
async def get_embedding(text: str) -> Optional[list[float]]:
    """Generate embedding vector if API key is present."""
    if not _embedding_client:
        return None
    try:
        res = await _embedding_client.embeddings.create(
            input=text,
            model=settings.embedding_model,
            encoding_format="float",
        )
        return res.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding failed (fallback to lexical): {e}")
        return None


def _search_terms(text: str) -> set[str]:
    return {
        term for term in re.findall(r"[a-z0-9]+", text.lower())
        if len(term) > 2 and term not in SEARCH_STOP_WORDS
    }


def _card_search_text(card: dict) -> str:
    metadata = card.get("metadata") or {}
    return " ".join([
        card.get("title", ""),
        card.get("content", ""),
        " ".join(str(keyword) for keyword in (metadata.get("keywords") or [])),
        json.dumps(metadata.get("facts") or {}),
    ])


def _rank_local_matches(cards: list[dict], query: str, limit: int) -> list[dict]:
    query_terms = _search_terms(query)
    if not query_terms:
        return []

    ranked = []
    for card in cards:
        card_terms = _search_terms(_card_search_text(card))
        overlap = query_terms & card_terms
        if not overlap:
            continue

        title_terms = _search_terms(card.get("title", ""))
        keyword_terms = _search_terms(" ".join(str(k) for k in (card.get("metadata") or {}).get("keywords", [])))
        score = len(overlap) / len(query_terms)
        score += len(overlap & title_terms) * 0.15
        score += len(overlap & keyword_terms) * 0.1
        ranked.append((score, card))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {**card, "similarity": round(min(score, 1.0), 3), "retrieval_type": "local"}
        for score, card in ranked[:limit]
    ]

# ──────────────────────────────────────────────
# Step 2: Retrieve relevant knowledge
# ──────────────────────────────────────────────
async def retrieve_knowledge(query: str, limit: int = 5, category: str = None) -> list[dict]:
    """Hybrid search: exact pattern -> lexical -> vector fallback."""
    matched_cards = []
    seen = set()
    all_cards = []

    # 1. Exact pattern match in python
    # We fetch all cards or use a quick query. Since dataset is small, fetching all is okay for pattern match.
    try:
        all_res = _supabase.table('knowledge').select('id, title, content, source, source_url, metadata').execute()
        all_cards = all_res.data or []
        for card in all_cards:
            meta = card.get('metadata') or {}
            patterns = meta.get('question_patterns', [])
            for pattern in patterns:
                if pattern.lower() in query.lower():
                    matched_cards.append({**card, 'similarity': 1.0, 'retrieval_type': 'pattern'})
                    seen.add(card['id'])
                    break
    except Exception as e:
        logger.error(f"Pattern match error: {e}")

    if len(matched_cards) >= limit:
        return matched_cards[:limit]

    # 2. Local token matching handles natural questions when full-text search
    # would require every query term to appear in the same record.
    for result in _rank_local_matches(all_cards, query, limit):
        if result["id"] not in seen:
            matched_cards.append(result)
            seen.add(result["id"])

    if len(matched_cards) >= limit:
        return matched_cards[:limit]

    # 3. Lexical search (PostgreSQL full-text via RPC)
    try:
        lexical_results = _supabase.rpc(
            'hybrid_search',
            {
                'query_text': query,
                'match_count': limit,
                'filter_category': category
            }
        ).execute()
        for res in (lexical_results.data or []):
            if res['id'] not in seen:
                matched_cards.append({**res, 'similarity': 0.9, 'retrieval_type': 'lexical'})
                seen.add(res['id'])
    except Exception as e:
        logger.error(f"Lexical search error: {e}")

    if len(matched_cards) >= limit:
        return matched_cards[:limit]

    # 4. Vector search (if available)
    embedding = await get_embedding(query)
    if embedding:
        try:
            vector_results = _supabase.rpc(
                'match_knowledge',
                {
                    'query_embedding': embedding,
                    'match_threshold': 0.45,
                    'match_count': limit,
                    'filter_category': category,
                }
            ).execute()
            for res in (vector_results.data or []):
                if res['id'] not in seen:
                    matched_cards.append({**res, 'similarity': res.get('similarity', 0.8), 'retrieval_type': 'vector'})
                    seen.add(res['id'])
        except Exception as e:
            logger.error(f"Vector search error: {e}")

    return matched_cards[:limit]

# ──────────────────────────────────────────────
# Step 3: Build the context string
# ──────────────────────────────────────────────
def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No specific SDIT information was found for this query."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        source = chunk.get("source", "")
        parts.append(f"[{i}] {title}\nSource: {source}\n{content}")

    return "\n\n---\n\n".join(parts)

# ──────────────────────────────────────────────
# Step 4: Call the LLM
# ──────────────────────────────────────────────
async def call_llm(messages: list[dict]) -> str:
    try:
        response = await _llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
            # Extra headers some platforms like OpenRouter expect
            extra_headers={
                "HTTP-Referer": "https://sdit-techbot.local",
                "X-Title": "SDIT Tech-Bot",
            }
        )
        if not response.choices:
            raise RuntimeError("LLM returned no choices")

        message = response.choices[0].message
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content

        refusal = getattr(message, "refusal", None)
        if isinstance(refusal, str) and refusal.strip():
            return refusal

        raise RuntimeError("LLM returned no usable text content")
    except Exception as e:
        logger.error(f"LLM API Error: {e}")
        # Funny/subtle error messages as requested
        error_text = str(e).lower()
        if "free-models-per-day" in error_text:
            raise Exception("The free chat-model daily limit has been reached. Wait for the provider reset or add provider credits/select a paid model.")
        elif "rate limit" in error_text or "429" in error_text:
            raise Exception("The chat provider is rate-limiting requests. Please try again later or use a model with available quota.")
        elif "unauthorized" in str(e).lower() or "key" in str(e).lower():
            raise Exception("Oops! The API refused to talk (authentication issue). Please check the keys.")
        elif "connection" in str(e).lower() or "timeout" in str(e).lower():
            raise Exception("The server is taking a nap. Connection timed out. Please try again.")
        else:
            raise Exception("Yikes! The API is throwing a tantrum right now. Please try again later.")

# ──────────────────────────────────────────────
# Step 5: Full RAG pipeline
# ──────────────────────────────────────────────
async def run_rag_pipeline(
    user_query: str,
    conversation_history: list[dict],
) -> tuple[str, list[dict]]:
    chunks = await retrieve_knowledge(user_query)
    context = build_context(chunks)

    context_message = (
        f"CONTEXT FROM SDIT KNOWLEDGE BASE:\n\n{context}\n\n"
        f"---\n\nUsing the above context, answer the student's question."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history[-6:])

    messages.append({"role": "user", "content": context_message})
    messages.append({"role": "user", "content": user_query})

    answer = await call_llm(messages)

    sources = [
        {
            "title": c.get("title", "Unknown"),
            "source": c.get("source", "Unknown"),
            "source_url": c.get("source_url", ""),
            "similarity": round(c.get("similarity", 0), 3),
        }
        for c in chunks
    ]

    return answer, sources
