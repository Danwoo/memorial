@echo off
chcp 65001 > nul
echo ===================================================
echo   Memoir AI - 완전 복구 및 실행 스크립트
echo ===================================================
echo.

echo [1/5] 기존 프로세스 종료...
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/5] Backend 의존성 설치 (uv sync)...
cd backend
call uv sync --link-mode=copy
if %errorlevel% neq 0 (
    echo ❌ uv sync 실패. pip로 직접 설치합니다...
    call .venv\Scripts\pip install langchain-community langchain-openai neo4j sniffio httpx beautifulsoup4 pydantic-settings supabase python-dotenv
)
cd ..

echo [3/5] 모듈 임포트 테스트...
cd backend
.venv\Scripts\python -c "from app.main import app; print('✅ 모든 모듈 정상!')"
if %errorlevel% neq 0 (
    echo ❌ 모듈 임포트 실패. 오류 메시지를 확인하세요.
    pause
    exit /b
)
cd ..

echo [4/5] Backend 서버 시작...
start "Memoir Backend" cmd /k "cd backend && .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [5/5] Frontend 서버 시작...
start "Memoir Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo ✅ 완료! 서버가 새 창에서 실행됩니다.
echo.
echo 👉 Web App: http://localhost:5173
echo 👉 API Docs: http://localhost:8000/docs
echo ===================================================
pause
