-- ==========================================
-- Vector Search Function (RPC)
-- ==========================================

-- 1. 유사도 검색 함수
-- Supabase API에서 rpc()로 호출하여 사용합니다.
create or replace function match_memories (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter jsonb default '{}'
)
returns table (
  id uuid,
  content text,
  title text,
  summary text,
  source_type text,
  created_at timestamptz,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    memories.id,
    memories.content,
    memories.title,
    memories.summary,
    memories.source_type,
    memories.created_at,
    1 - (memories.embedding <=> query_embedding) as similarity
  from memories
  where 1 - (memories.embedding <=> query_embedding) > match_threshold
  -- 메타데이터 필터링 (필요 시)
  and (filter = '{}'::jsonb or memories.metadata @> filter)
  order by memories.embedding <=> query_embedding
  limit match_count;
end;
$$;
