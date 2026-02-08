@echo off
chcp 65001 > nul
echo ===================================================
echo   Memoir AI - Full System Start
echo ===================================================
echo.

echo [1/4] Python 프로세스 종료...
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Backend 가상환경 재구성 (시간이 걸립니다)...
cd backend
if exist .venv (
    echo      .venv 폴더 삭제 중...
    rmdir /s /q .venv 2>nul
    timeout /t 3 /nobreak >nul
)
echo      패키지 설치 중 (uv sync)...
call uv sync --link-mode=copy
if %errorlevel% neq 0 (
    echo ❌ 패키지 설치 실패. 다시 시도합니다...
    call uv sync --link-mode=copy
)
cd ..

echo [3/4] Backend 서버 시작 (Port 8000)...
start "Memoir Backend" cmd /k "cd backend && .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [4/4] Frontend 서버 시작 (Port 5173)...
start "Memoir Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo ✅ 서버가 새 창에서 실행됩니다.
echo    잠시 후(약 10초 뒤) 아래 주소로 접속하세요.
echo.
echo 👉 Web App: http://localhost:5173
echo 👉 API Docs: http://localhost:8000/docs
echo ===================================================
pause
