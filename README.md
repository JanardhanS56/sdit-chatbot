# SDIT Tech-Bot

An AI campus assistant for Shree Devi Institute of Technology (SDIT), Mangaluru. The project combines a Next.js chat interface with a FastAPI retrieval-augmented generation (RAG) backend, Supabase knowledge storage, and an OpenAI-compatible LLM gateway.

## Why This Project

SDIT Tech-Bot turns official college information into a searchable conversational experience for students, faculty, and visitors. It retrieves relevant verified records, passes only that context to the language model, and displays the sources used for each answer.

### Features

- Conversational answers for admissions, courses, campus facilities, placements, and college information
- Hybrid retrieval with exact question patterns, local lexical ranking, PostgreSQL search, and optional embeddings
- Source links and similarity scores returned with every answer
- Student, faculty, and visitor modes with suggested questions
- Complaint submission and answer feedback endpoints backed by Supabase
- Session history, health checks, CORS configuration, and responsive UI
- Safe local crawler that respects `robots.txt`, domain boundaries, and rate limits

## Architecture

```text
Next.js frontend -> FastAPI API -> hybrid RAG retrieval -> Supabase PostgreSQL/pgvector
									  |
									  +-> OpenAI-compatible chat and embedding APIs
```

## Stack

- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, Pydantic Settings
- Data: Supabase PostgreSQL with optional pgvector embeddings
- AI: OpenAI-compatible chat and embedding APIs, configured for OpenRouter by default
- Deployment target: Vercel for the frontend and Railway or Render for the backend

## Repository Layout

```text
backend/       FastAPI routes, settings, and RAG pipeline
frontend/      Next.js application
data/processed Curated knowledge records used for ingestion
scripts/       Crawler, cleaning, and Supabase ingestion utilities
supabase/      Database schema and migration SQL
tests/         Automated tests for the crawler
```

Raw crawl output, local credentials, build artifacts, and the original source PDF are intentionally excluded from version control. The curated `data/processed/manual_cards.json` file is the default ingestion source.

## Run Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project
- An API key for an OpenAI-compatible chat provider

### Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Set-Location frontend
npm install
Set-Location ..
```

### Configure

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

Fill in the values in those files. Never commit them. The backend requires `SUPABASE_URL`, `SUPABASE_KEY`, and `LLM_API_KEY`; `SUPABASE_SERVICE_ROLE_KEY` is needed only for ingestion. See [SETUP_GUIDE.md](SETUP_GUIDE.md) for the complete configuration and deployment steps.

### Create the database and ingest data

Run [supabase/schema.sql](supabase/schema.sql) in the Supabase SQL editor, then run:

```powershell
py scripts/ingest.py --file data/processed/manual_cards.json --no-embeddings
```

Embeddings are optional. Without them, the application uses its lexical and PostgreSQL retrieval fallbacks.

### Start the application

```powershell
# Terminal 1
Set-Location backend
py -m uvicorn main:app --reload --port 8000

# Terminal 2
Set-Location frontend
npm run dev
```

Open `http://localhost:3000`. The API health check is available at `http://localhost:8000/health`.

## Tests and Checks

```powershell
py -m unittest discover -s tests
Set-Location frontend
npm run build
```

## Deployment

1. Push this repository to GitHub after reviewing `git status` and confirming no `.env` files are staged.
2. Deploy `frontend/` as a Vercel project and set `NEXT_PUBLIC_API_URL` to the public backend URL.
3. Deploy `backend/` to Railway or Render and add the variables from `backend/.env.example`.
4. Set backend `CORS_ORIGINS` to the Vercel URL, run the Supabase schema, and ingest the curated knowledge file.
5. Verify `/health`, chat, source links, feedback, and complaint submission in the production UI.

## Resume Summary

**SDIT Tech-Bot | Full-stack RAG campus assistant**

Built a production-oriented campus chatbot with Next.js, FastAPI, Supabase, and hybrid retrieval. Implemented source-grounded responses, optional vector search, a rate-limited crawler, structured knowledge ingestion, feedback and complaint workflows, and separate frontend/backend deployment configuration.

## Data and Scope

Knowledge is based on curated public SDIT information and should be reviewed when official policies, fees, dates, or contact details change. The chatbot is an informational interface, not a replacement for official college support.
