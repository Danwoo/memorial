-- ==========================================
-- Vector Search Function (RPC)
-- ==========================================

-- 1. 유사도 검색 함수
-- Supabase API에서 rpc()로 호출하여 사용합니다.
-- filter jsonb에서 user_id, source_type은 top-level 컬럼으로 필터링하고,
-- 나머지 키는 metadata jsonb @> 연산으로 필터링합니다.
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
  -- user_id: top-level 컬럼 필터
  and (filter->>'user_id' is null or memories.user_id = (filter->>'user_id')::uuid)
  -- source_type: top-level 컬럼 필터
  and (filter->>'source_type' is null or memories.source_type = filter->>'source_type')
  order by memories.embedding <=> query_embedding
  limit match_count;
end;
$$;
