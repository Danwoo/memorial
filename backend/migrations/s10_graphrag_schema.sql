-- Migration s10: GraphRAG Supabase 스키마
-- graph_entities: 엔티티 임베딩 영구 저장
-- graph_communities: Louvain 커뮤니티 요약 + 임베딩

-- ─── graph_entities ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS graph_entities (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name         TEXT        NOT NULL,
  entity_type  TEXT        NOT NULL DEFAULT 'Concept',
  description  TEXT,
  embedding    vector(1536),
  updated_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, name)
);

ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own graph entities"
  ON graph_entities FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS graph_entities_user_idx
  ON graph_entities(user_id);

CREATE INDEX IF NOT EXISTS graph_entities_embedding_idx
  ON graph_entities USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

-- ─── graph_communities ────────────────────────────────────────────────────
-- level: 0=fine(resolution 0.3), 1=mid(1.0), 2=coarse(3.0)
CREATE TABLE IF NOT EXISTS graph_communities (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  level             INT         NOT NULL,
  community_id      INT         NOT NULL,
  entities          TEXT[]      NOT NULL DEFAULT '{}',
  entity_count      INT         DEFAULT 0,
  summary           TEXT,
  summary_embedding vector(1536),
  updated_at        TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, level, community_id)
);

ALTER TABLE graph_communities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own graph communities"
  ON graph_communities FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS graph_communities_user_level_idx
  ON graph_communities(user_id, level);

CREATE INDEX IF NOT EXISTS graph_communities_embedding_idx
  ON graph_communities USING ivfflat (summary_embedding vector_cosine_ops)
  WITH (lists = 50);

-- ─── RPC: 커뮤니티 요약 의미 유사도 검색 ─────────────────────────────────
CREATE OR REPLACE FUNCTION match_graph_communities(
  query_embedding    vector(1536),
  p_user_id          UUID,
  p_level            INT     DEFAULT 1,
  match_count        INT     DEFAULT 10,
  similarity_threshold FLOAT DEFAULT 0.45
)
RETURNS TABLE (
  id           UUID,
  level        INT,
  community_id INT,
  entities     TEXT[],
  summary      TEXT,
  similarity   FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    gc.id,
    gc.level,
    gc.community_id,
    gc.entities,
    gc.summary,
    1 - (gc.summary_embedding <=> query_embedding) AS similarity
  FROM graph_communities gc
  WHERE gc.user_id = p_user_id
    AND gc.level   = p_level
    AND gc.summary_embedding IS NOT NULL
    AND 1 - (gc.summary_embedding <=> query_embedding) >= similarity_threshold
  ORDER BY gc.summary_embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ─── RPC: 엔티티 의미 유사도 검색 ────────────────────────────────────────
CREATE OR REPLACE FUNCTION match_graph_entities(
  query_embedding    vector(1536),
  p_user_id          UUID,
  match_count        INT     DEFAULT 10,
  similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
  id          UUID,
  name        TEXT,
  entity_type TEXT,
  description TEXT,
  similarity  FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ge.id,
    ge.name,
    ge.entity_type,
    ge.description,
    1 - (ge.embedding <=> query_embedding) AS similarity
  FROM graph_entities ge
  WHERE ge.user_id = p_user_id
    AND ge.embedding IS NOT NULL
    AND 1 - (ge.embedding <=> query_embedding) >= similarity_threshold
  ORDER BY ge.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
