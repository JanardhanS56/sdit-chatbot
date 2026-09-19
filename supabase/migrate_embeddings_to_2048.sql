-- Run this once in the Supabase SQL Editor.
-- The current knowledge rows have no stored embeddings, so replacing the empty
-- vector column is safe and leaves all text and metadata intact.

drop function if exists match_knowledge(vector, double precision, integer, text);
drop function if exists hybrid_search(text, vector, double precision, integer, text);
drop index if exists knowledge_embedding_idx;

alter table knowledge drop column if exists embedding;
alter table knowledge add column embedding vector(2048);

-- pgvector IVFFlat indexes support at most 2000 dimensions. NVIDIA's model
-- returns 2048, so this small 78-card dataset uses an exact scan instead.

alter table knowledge add column if not exists search_tsv tsvector;

create index if not exists knowledge_search_tsv_idx
  on knowledge using gin (search_tsv);

create or replace function update_search_tsv() returns trigger as $$
begin
  new.search_tsv :=
    setweight(to_tsvector('english', coalesce(new.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.content, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(new.metadata->>'keywords', '')), 'C') ||
    setweight(to_tsvector('english', coalesce(new.metadata->>'question_patterns', '')), 'B');
  return new;
end;
$$ language plpgsql;

drop trigger if exists tsvector_update on knowledge;
create trigger tsvector_update
  before insert or update on knowledge
  for each row execute function update_search_tsv();

update knowledge
set search_tsv =
  setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(content, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(metadata->>'keywords', '')), 'C') ||
  setweight(to_tsvector('english', coalesce(metadata->>'question_patterns', '')), 'B');

create or replace function match_knowledge (
  query_embedding vector(2048),
  match_threshold float default 0.45,
  match_count int default 6,
  filter_category text default null
)
returns table (
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
    and k.embedding is not null
    and 1 - (k.embedding <=> query_embedding) > match_threshold
  order by k.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function hybrid_search (
  query_text text,
  query_embedding vector(2048) default null,
  match_threshold float default 0.5,
  match_count int default 6,
  filter_category text default null
)
returns table (
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
    case
      when query_embedding is not null and k.embedding is not null
        then 1 - (k.embedding <=> query_embedding)
      else ts_rank(k.search_tsv, plainto_tsquery('english', query_text))
    end as similarity
  from knowledge k
  where
    (filter_category is null or k.category = filter_category)
    and (
      (query_embedding is not null and k.embedding is not null
        and 1 - (k.embedding <=> query_embedding) > match_threshold)
      or
      (query_embedding is null and k.search_tsv @@ plainto_tsquery('english', query_text))
    )
  order by similarity desc
  limit match_count;
$$;