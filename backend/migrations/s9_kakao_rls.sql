-- S9: 카카오 관련 테이블 RLS 추가
-- 백엔드가 service_role_key를 사용하므로 Supabase 클라이언트 직접 접근을 방어하기 위한 RLS
-- user_id 컬럼 타입이 테이블마다 다를 수 있으므로 양쪽 ::text 캐스트로 통일

-- ============================================
-- 1. RLS 활성화
-- ============================================
ALTER TABLE kakao_bot_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE kakao_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE kakao_channel_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE kakao_delivery_log ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 2. RLS 정책 추가 (본인 데이터만 접근)
-- ============================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kakao_bot_settings' AND policyname = 'kakao_bot_settings_user_policy') THEN
    EXECUTE 'CREATE POLICY kakao_bot_settings_user_policy ON kakao_bot_settings FOR ALL USING (user_id::text = auth.uid()::text)';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kakao_tokens' AND policyname = 'kakao_tokens_user_policy') THEN
    EXECUTE 'CREATE POLICY kakao_tokens_user_policy ON kakao_tokens FOR ALL USING (user_id::text = auth.uid()::text)';
  END IF;

  -- kakao_channel_mappings: user_id 컬럼 유무 확인
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'kakao_channel_mappings' AND column_name = 'user_id'
  ) THEN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kakao_channel_mappings' AND policyname = 'kakao_channel_mappings_user_policy') THEN
      EXECUTE 'CREATE POLICY kakao_channel_mappings_user_policy ON kakao_channel_mappings FOR ALL USING (user_id::text = auth.uid()::text)';
    END IF;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kakao_delivery_log' AND policyname = 'kakao_delivery_log_user_policy') THEN
    EXECUTE 'CREATE POLICY kakao_delivery_log_user_policy ON kakao_delivery_log FOR ALL USING (user_id::text = auth.uid()::text)';
  END IF;
END
$$;
