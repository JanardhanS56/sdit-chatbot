"""
SDIT Tech-Bot — Knowledge Ingestion Script
Handles embedding fallback gracefully.
"""

import json
import time
import sys
import os
import argparse
from supabase import create_client
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

DEFAULT_KNOWLEDGE_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/manual_cards.json")

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in backend/.env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
openai_client = OpenAI(
    api_key=EMBEDDING_API_KEY,
    base_url=EMBEDDING_API_BASE,
    max_retries=0,
) if EMBEDDING_API_KEY else None

def get_embedding(text: str) -> list[float]:
    if not openai_client:
        return None
    try:
        res = openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
            encoding_format="float",
        )
        return res.data[0].embedding
    except Exception as e:
        print(f"Embedding failed: {e}")
        return None

def embed_record(record: dict) -> str:
    parts = [
        record.get("title", ""),
        record.get("category", ""),
        record.get("subcategory", ""),
        record.get("content", ""),
    ]
    keywords = record.get("keywords", [])
    if not keywords:
        keywords = record.get("metadata", {}).get("keywords", [])
    if keywords:
        parts.append("Keywords: " + ", ".join(keywords))
    return " | ".join(p for p in parts if p)

def ingest(knowledge_file: str, clear_first: bool = False, no_embeddings: bool = False):
    print("=== SDIT Tech-Bot Knowledge Ingestion ===")
    if clear_first:
        print("Clearing existing knowledge rows...")
        supabase.table("knowledge").delete().neq("title", "").execute()

    if no_embeddings:
        print("Note: Embeddings disabled for this run. Using lexical search data only.")
    elif not openai_client:
        print("Note: EMBEDDING_API_KEY not found. Falling back to purely lexical ingestion (no embeddings).")

    with open(knowledge_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    success, failed = 0, 0

    for i, record in enumerate(records, 1):
        title = record.get("title", f"Record {i}")
        print(f"[{i}/{len(records)}] Processing: {title}")

        try:
            embed_text = embed_record(record)
            embedding = None if no_embeddings else get_embedding(embed_text)
            if openai_client and not no_embeddings and not embedding:
                raise RuntimeError("Embedding was unavailable; row was not written")

            metadata = dict(record.get("metadata") or {})
            metadata["keywords"] = record.get("keywords", metadata.get("keywords", []))
            metadata["question_patterns"] = record.get("question_patterns", [])
            metadata["facts"] = record.get("facts", {})
            metadata["priority"] = record.get("priority", 5)
            metadata["is_historical"] = record.get("is_historical", False)
            metadata["verified"] = record.get("verified", True)
            metadata["original_id"] = record.get("id")
            
            row = {
                "category": record.get("category", "general"),
                "subcategory": record.get("subcategory"),
                "title": record.get("title", ""),
                "content": record.get("content", ""),
                "source": record.get("source"),
                "source_url": record.get("source_url"),
                "academic_year": record.get("academic_year"),
                "metadata": metadata,
            }
            if embedding:
                row["embedding"] = embedding

            supabase.table("knowledge").upsert(row, on_conflict="title").execute()
            success += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

        time.sleep(0.1)

    print(f"\n=== Complete ===\n  Success: {success}\n  Failed:  {failed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge records")
    parser.add_argument("--file", default=DEFAULT_KNOWLEDGE_FILE, help="JSON file")
    parser.add_argument("--clear", action="store_true", help="Delete existing knowledge rows before ingestion")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation and use lexical search")
    args = parser.parse_args()
    ingest(args.file, clear_first=args.clear, no_embeddings=args.no_embeddings)
