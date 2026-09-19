-- SDIT Tech-Bot Database Schema
-- Run this in Supabase SQL editor

-- Enable pgvector extension for semantic search
create extension if not exists vector;

-- ============================================================
-- KNOWLEDGE BASE TABLE
-- Core table: every piece of college information lives here
-- ============================================================
create table if not exists knowledge (
  id            bigserial primary key,
  category      text not null,        -- e.g. 'college_info', 'departments', 'admissions'
  subcategory   text,                 -- e.g. 'history', 'fees', 'hostel'
  title         text not null,
  content       text not null,
  source        text,                 -- e.g. 'SDIT Official Website'
  source_url    text,
  academic_year text,                 -- e.g. '2024-25' — critical for fees/dates
  metadata      jsonb default '{}',
  embedding     vector(2048),         -- NVIDIA nemotron-3-embed-1b dimensions
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create unique index if not exists knowledge_title_unique_idx
  on knowledge(title);

-- The backend uses the public anon key for read-only vector retrieval.
alter table knowledge enable row level security;
drop policy if exists knowledge_read_public on knowledge;
create policy knowledge_read_public
  on knowledge for select
  to anon, authenticated
  using (true);

-- NVIDIA's 2048-dimensional embeddings exceed pgvector IVFFlat's 2000-dimension
-- index limit. The current small dataset uses exact similarity scans.

-- Index for category filtering
create index if not exists knowledge_category_idx on knowledge(category);
create index if not exists knowledge_subcategory_idx on knowledge(subcategory);

-- ============================================================
-- CONVERSATIONS TABLE
-- Stores session context for multi-turn conversations
-- ============================================================
create table if not exists conversations (
  id            uuid primary key default gen_random_uuid(),
  session_id    text not null unique,
  messages      jsonb default '[]',   -- array of {role, content, timestamp}
  user_type     text default 'student', -- 'student', 'faculty', 'visitor'
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create index if not exists conversations_session_idx on conversations(session_id);

-- ============================================================
-- FEEDBACK TABLE
-- Collects thumbs up/down and free-form feedback
-- ============================================================
create table if not exists feedback (
  id            bigserial primary key,
  session_id    text,
  question      text not null,
  answer        text not null,
  rating        smallint check (rating in (1, -1)), -- 1=helpful, -1=not helpful
  comment       text,
  created_at    timestamptz default now()
);

-- ============================================================
-- COMPLAINTS TABLE
-- Separates complaints from regular chatbot conversations
-- ============================================================
create table if not exists complaints (
  id            bigserial primary key,
  student_name  text,
  student_id    text,
  category      text,   -- 'academic', 'facility', 'hostel', 'other'
  description   text not null,
  status        text default 'submitted', -- 'submitted', 'in_review', 'resolved'
  created_at    timestamptz default now()
);

-- ============================================================
-- MATCH KNOWLEDGE FUNCTION
-- Used by the backend for semantic retrieval
-- ============================================================
create or replace function match_knowledge (
  query_embedding vector(2048),
  match_threshold float default 0.5,
  match_count     int default 6,
  filter_category text default null
)
returns table (
  id          bigint,
  category    text,
  subcategory text,
  title       text,
  content     text,
  source      text,
  source_url  text,
  academic_year text,
  metadata    jsonb,
  similarity  float
)
language sql stable
as $$
  select
    k.id,
    k.category,
    k.subcategory,
    k.title,
    k.content,
    k.source,
    k.source_url,
    k.academic_year,
    k.metadata,
    1 - (k.embedding <=> query_embedding) as similarity
  from knowledge k
  where
    (filter_category is null or k.category = filter_category)
    and 1 - (k.embedding <=> query_embedding) > match_threshold
  order by k.embedding <=> query_embedding
  limit match_count;
$$;

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger knowledge_updated_at
  before update on knowledge
  for each row execute function update_updated_at();

create trigger conversations_updated_at
  before update on conversations
  for each row execute function update_updated_at();

-- ============================================================
-- FULL-TEXT & HYBRID SEARCH
-- ============================================================
-- Add full-text search column
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS search_tsv tsvector;

-- Create an index for fast full-text search
CREATE INDEX IF NOT EXISTS knowledge_search_tsv_idx ON knowledge USING GIN (search_tsv);

-- Function to automatically update the search_tsv column when title, content, or metadata changes
CREATE OR REPLACE FUNCTION update_search_tsv() RETURNS trigger AS $$
BEGIN
  NEW.search_tsv :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.content, '')), 'B') ||
    setweight(to_tsvector('english', coalesce((NEW.metadata->>'keywords'), '')), 'C') ||
    setweight(to_tsvector('english', coalesce((NEW.metadata->>'question_patterns'), '')), 'B');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Trigger to run the function before insert or update
DROP TRIGGER IF EXISTS tsvector_update ON knowledge;
CREATE TRIGGER tsvector_update
  BEFORE INSERT OR UPDATE ON knowledge
  FOR EACH ROW EXECUTE FUNCTION update_search_tsv();

-- RPC function for hybrid search (full-text + optional semantic)
CREATE OR REPLACE FUNCTION hybrid_search (
  query_text text,
  query_embedding vector(2048) default null,
  match_threshold float default 0.5,
  match_count int default 6,
  filter_category text default null
)
RETURNS TABLE (
  id bigint,
  category text,
  subcategory text,
  title text,
  content text,
  source text,
  source_url text,
  academic_year text,
  metadata jsonb,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    k.id,
    k.category,
    k.subcategory,
    k.title,
    k.content,
    k.source,
    k.source_url,
    k.academic_year,
    k.metadata,
    CASE 
      WHEN query_embedding IS NOT NULL THEN 1 - (k.embedding <=> query_embedding)
      ELSE ts_rank(k.search_tsv, plainto_tsquery('english', query_text))
    END as similarity
  FROM knowledge k
  WHERE
    (filter_category IS NULL OR k.category = filter_category)
    AND (
      (query_embedding IS NOT NULL AND 1 - (k.embedding <=> query_embedding) > match_threshold)
      OR 
      (query_embedding IS NULL AND k.search_tsv @@ plainto_tsquery('english', query_text))
    )
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
