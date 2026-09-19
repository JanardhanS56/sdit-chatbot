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

-- Update existing rows
UPDATE knowledge SET id = id;

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
