-- S8-6: Supabase 스키마 최적화 + 프로덕션 준비
-- 인덱스 추가 + RLS 정책 적용

-- ============================================
-- 1. B-tree 인덱스 추가 (memories)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_source_type ON memories USING btree (source_type);
CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories USING btree (user_id, created_at DESC);

-- ============================================
-- 2. B-tree 인덱스 추가 (chat_sessions)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_created ON chat_sessions USING btree (user_id, created_at DESC);

-- ============================================
-- 3. B-tree 인덱스 추가 (chat_feedback)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_chat_feedback_session ON chat_feedback USING btree (session_id);

-- ============================================
-- 4. RLS (Row Level Security) 활성화
-- ============================================
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_memory_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_notification_settings ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 5. RLS 정책 추가 (누락된 테이블만)
-- ============================================
DO $$
BEGIN
  -- chat_messages: 세션 소유자만 접근
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'chat_messages' AND policyname = 'chat_messages_user_policy') THEN
    EXECUTE 'CREATE POLICY chat_messages_user_policy ON chat_messages FOR ALL USING (
      session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid())
    )';
  END IF;

  -- journal_memory_links: 저널 소유자만 접근
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_memory_links' AND policyname = 'jml_user_policy') THEN
    EXECUTE 'CREATE POLICY jml_user_policy ON journal_memory_links FOR ALL USING (
      journal_id IN (SELECT id FROM journals WHERE user_id = auth.uid())
    )';
  END IF;

  -- push_subscriptions: 본인 구독만 접근
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'push_subscriptions' AND policyname = 'push_sub_user_policy') THEN
    EXECUTE 'CREATE POLICY push_sub_user_policy ON push_subscriptions FOR ALL USING (
      user_id = auth.uid()
    )';
  END IF;

  -- user_notification_settings: 본인 설정만 접근
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'user_notification_settings' AND policyname = 'notif_settings_user_policy') THEN
    EXECUTE 'CREATE POLICY notif_settings_user_policy ON user_notification_settings FOR ALL USING (
      user_id = auth.uid()
    )';
  END IF;
END
$$;
