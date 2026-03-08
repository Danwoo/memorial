#!/usr/bin/env python3
"""
Supabase & KuzuDB 연결 검증 스크립트
Backend 환경에서 실행: cd backend && python ../scripts/validate-db.py
"""

import os
import sys
import json
from pathlib import Path

def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / "backend" / ".env"
    env = {}

    if not env_file.exists():
        print(f"✗ .env 파일 없음: {env_file}")
        return env

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env[key] = value

    return env

def check_supabase(env):
    """Check Supabase connection"""
    print("\n[1] Supabase 연결 검증...")

    url = env.get('SUPABASE_URL')
    key = env.get('SUPABASE_ANON_KEY')

    if not url or not key:
        print("  ✗ SUPABASE_URL 또는 SUPABASE_ANON_KEY 미설정")
        return False

    print(f"  URL: {url}")

    try:
        # supabase-py 설치 필요: pip install supabase
        from supabase import create_client

        client = create_client(url, key)
        response = client.table('scraps').select('count').limit(1).execute()

        print("  ✓ Supabase 연결 성공")
        return True

    except ImportError:
        print("  ⚠ supabase 라이브러리 미설치")
        print("    설치: pip install supabase")
        return False
    except Exception as e:
        print(f"  ✗ 연결 실패: {str(e)[:100]}")
        return False

def check_kuzu(env):
    """Check KuzuDB connection"""
    print("\n[2] KuzuDB 연결 검증...")

    kuzu_path = Path(__file__).parent.parent / "backend" / "kuzu_data"

    if not kuzu_path.exists():
        print(f"  ⚠ KuzuDB 폴더 없음: {kuzu_path}")
        print("    → 첫 실행 시 자동 생성됨")
        return None

    try:
        import kuzu

        db = kuzu.database.Database(str(kuzu_path))
        conn = kuzu.connection.Connection(db)

        # 그래프 노드 수 확인
        result = conn.execute("MATCH (n) RETURN COUNT(n) AS count")
        count = 0
        while result.has_next():
            row = result.get_next()
            count = row['count']

        print(f"  ✓ KuzuDB 연결 성공")
        print(f"    그래프 노드: {count} 개")
        return True

    except ImportError:
        print("  ⚠ kuzu 라이브러리 미설치")
        print("    설치: pip install kuzu")
        return False
    except Exception as e:
        print(f"  ✗ 연결 실패: {str(e)[:100]}")
        return False

def check_api_keys(env):
    """Check API keys configuration"""
    print("\n[3] API 키 검증...")

    keys = [
        ('OPENAI_API_KEY', 'OpenAI'),
        ('GOOGLE_API_KEY', 'Google Gemini'),
        ('OPENROUTER_API_KEY', 'OpenRouter'),
        ('UPSTAGE_API_KEY', 'Upstage (optional)'),
        ('KAKAO_REST_API_KEY', 'Kakao Botfriends'),
    ]

    all_ok = True
    for key_name, description in keys:
        value = env.get(key_name, '')
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f"  ✓ {description}: 설정됨 ({masked})")
        else:
            status = "⚠" if 'optional' in description else "✗"
            print(f"  {status} {description}: 미설정")
            if 'optional' not in description:
                all_ok = False

    return all_ok

def check_cors(env):
    """Check CORS configuration"""
    print("\n[4] CORS 설정 검증...")

    allowed_origins = env.get('ALLOWED_ORIGINS', '')

    if not allowed_origins:
        print("  ✗ ALLOWED_ORIGINS 미설정")
        return False

    origins = [o.strip() for o in allowed_origins.split(',')]

    required = [
        'http://localhost:5173',
        'http://localhost:3000',
        'https://memoir-knowledge.vercel.app'
    ]

    print(f"  설정된 origin: {len(origins)} 개")
    for origin in origins:
        status = "✓" if origin in required else "ℹ"
        print(f"    {status} {origin}")

    missing = [r for r in required if r not in origins]
    if missing:
        print(f"  ⚠ 누락된 origin: {missing}")
        return False

    return True

def main():
    print("=" * 60)
    print("Memoir 프로젝트 - DB & API 검증")
    print("=" * 60)

    env = load_env()
    if not env:
        print("✗ 환경변수를 읽을 수 없습니다")
        sys.exit(1)

    results = {
        'Supabase': check_supabase(env),
        'KuzuDB': check_kuzu(env),
        'API Keys': check_api_keys(env),
        'CORS': check_cors(env),
    }

    print("\n" + "=" * 60)
    print("검증 결과 요약")
    print("=" * 60)

    for check_name, result in results.items():
        if result is True:
            status = "✓"
        elif result is False:
            status = "✗"
        else:
            status = "ⓘ"
        print(f"{status} {check_name}: {result}")

    print("\n" + "=" * 60)
    print("다음 단계:")
    print("1. 모든 검증이 ✓ 상태인지 확인")
    print("2. scripts/validate-api.sh로 API 엔드포인트 검증")
    print("3. frontend/npm run dev로 통합 테스트")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
