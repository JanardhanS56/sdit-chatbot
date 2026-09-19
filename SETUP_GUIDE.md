# SDIT Tech-Bot — Setup and Deployment Guide

This guide covers local development, database setup, data ingestion, and deployment. For a short project overview, start with [README.md](README.md).

---

## 1. Create Service Accounts

### 1a. Supabase (Free)
1. Go to https://supabase.com → Sign up
2. Create a new project (choose a strong DB password)
3. Go to Settings → API
4. Copy: **Project URL** and **anon public** key

### 1b. OpenRouter (Paid per token — very cheap)
1. Go to https://openrouter.ai → Sign up
2. Go to Keys → Create a new API key
3. Add ₹500–1000 credits (more than enough for the competition demo)
4. Copy the API key

---

## 2. Set Up Supabase Database

1. In your Supabase project, go to **SQL Editor**
2. Paste the contents of `supabase/schema.sql`
3. Click **Run**
4. Verify: go to Table Editor → you should see `knowledge`, `conversations`, `feedback`, `complaints` tables

If the chatbot returns no sources, run the following in Supabase SQL Editor so the backend's public anon key can read knowledge records while ingestion remains service-role-only:

```sql
alter table knowledge enable row level security;
drop policy if exists knowledge_read_public on knowledge;
create policy knowledge_read_public on knowledge
for select to anon, authenticated using (true);
```

---

## 3. Configure Environment Variables

### Backend
```bash
cd backend
cp .env.example .env
```
Edit `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
# Required only for local scripts/ingest.py; never expose this key in the frontend
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
LLM_API_KEY=your-provider-key
LLM_MODEL=google/gemini-2.0-flash-001
EMBEDDING_MODEL=openai/text-embedding-3-small
CORS_ORIGINS=http://localhost:3000
```

### Frontend
```bash
cd frontend
cp .env.example .env.local
```
Edit `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Install Dependencies

```bash
# Root & Backend Dependencies (including Crawler tools)
py -m pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

---

## 4.5 Crawl SDIT Website Content (Optional)

> [!WARNING]
> Web crawling must always respect `robots.txt` rules, website terms of service, rate limits, and target domain boundaries (`https://sdit.ac.in`). Do not bypass access restrictions or collect personal data.

To crawl public pages from the official SDIT website, extract clean structured text, and format records for ingestion:

```bash
# Default crawl (50 pages max, 1.5s delay)
python scripts/crawl_sdit.py

# Custom options example
python scripts/crawl_sdit.py --max-pages 20 --delay 2.0 --url https://sdit.ac.in/
```

### Output Locations:
- **Raw HTML files**: `data/raw/sdit/`
- **Crawl Manifest**: `data/raw/sdit/crawl_manifest.json`
- **Cleaned Knowledge Records**: `data/processed/crawled_knowledge_base.json`

### Review Before Ingestion:
1. Open `data/processed/crawled_knowledge_base.json` and review the generated JSON records.
2. Verify category, title, content quality, and keywords.
3. Once reviewed, you can ingest the records into Supabase by running `py scripts/ingest.py`.

The ingestion script requires `SUPABASE_SERVICE_ROLE_KEY` because Supabase Row Level Security blocks the public anon key from writing to the knowledge table. Get it from **Supabase → Project Settings → API → Secret keys** (or the legacy `service_role` key section). Keep it only in `backend/.env`; never put it in frontend environment variables or commit it.

---


## 5. Ingest Knowledge Data

This populates Supabase with all SDIT information.

```bash
cd scripts
py ingest.py --file ../data/processed/manual_cards.json --no-embeddings
```

Expected output:
```
=== SDIT Tech-Bot Knowledge Ingestion ===
Processing: Shree Devi Institute of Technology
  ✓ Inserted/updated successfully
...
=== Complete ===
  Success: 28
  Failed:  0
```

If any records fail, check your API keys and re-run.

---

## 6. Run Locally

Open two terminals:

**Terminal 1 — Backend:**
```bash
cd backend
py -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:3000 — the chatbot should load.

**Test it:**
- Ask: "Tell me about SDIT"
- Ask: "What are the library timings?"
- Ask: "How do I apply for admission?"

---

## 7. Update Knowledge Data

Open `data/processed/manual_cards.json` and add records for:
- [ ] More faculty names (get from SDIT website)
- [ ] Current fee structure (from admissions office)
- [ ] Current semester timetable
- [ ] Upcoming events
- [ ] Club details (IEEE contacts, NSS events)
- [ ] Exact hostel fees

Each record format:
```json
{
  "category": "facilities",
  "subcategory": "hostel",
  "title": "Boys Hostel Fee 2024-25",
  "content": "The boys hostel fee for 2024-25 is ...",
  "source": "SDIT Hostel Office",
  "source_url": "https://www.sdit.ac.in/hostel",
  "academic_year": "2024-25",
  "metadata": {"keywords": ["hostel", "fee", "boys", "2024"]}
}
```

After adding records, re-run: `py scripts/ingest.py --file data/processed/manual_cards.json --no-embeddings`

---

## 8. Deploy to Production

### Deploy Backend (Railway — Free tier)
1. Go to https://railway.app → Sign up
2. New Project → Deploy from GitHub
3. Select your repo, choose `backend/` folder
4. Add environment variables (same as `.env`)
5. Railway gives you a URL like `https://sdit-techbot-backend.railway.app`

### Deploy Frontend (Vercel — Free)
1. Push code to GitHub
2. Go to https://vercel.com → Import project
3. Set Root Directory to `frontend/`
4. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app`
5. Deploy

Update backend's `CORS_ORIGINS` to include your Vercel URL.

---

## 9. Test Production

- Visit your Vercel URL
- Test all 9 categories of questions
- Test on mobile
- Test error cases (type gibberish, ask out-of-scope questions)

---

## 10. Prepare a Demo

Questions to showcase during presentation:
1. "Tell me about the history of SDIT"
2. "What subjects are there in CSE 3rd semester?"
3. "How do I apply for admission?"
4. "What are the library timings?"
5. "Tell me about placement statistics"
6. "How do I download my hall ticket?"
7. "What clubs can I join at SDIT?"
8. "Tell me about hostel facilities"
9. "How should I prepare my resume for placement?"
10. "What is the anti-ragging policy?"

---

## Troubleshooting

**"Connection refused" on frontend:**
→ Backend is not running. Start it with `uvicorn main:app --reload`

**Embedding errors during ingest:**
→ Check `EMBEDDING_API_KEY`, `EMBEDDING_API_BASE`, and `EMBEDDING_MODEL` in `.env`, or use `--no-embeddings`.

**"match_knowledge function not found":**
→ You haven't run `supabase/schema.sql` yet

**Bot gives wrong answers:**
→ Add better data to `manual_cards.json` and re-run ingest

**CORS error in browser:**
→ Add your frontend URL to `CORS_ORIGINS` in backend `.env`