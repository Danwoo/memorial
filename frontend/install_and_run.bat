@echo off
chcp 65001 > nul
echo ===================================================
echo   Memoir AI - Frontend Setup
echo ===================================================
echo.

cd frontend

echo [1] 필요한 라이브러리 설치 중 (npm install)...
echo (시간이 조금 걸릴 수 있습니다)
call npm install
if %errorlevel% neq 0 (
    echo ❌ npm 설치 실패.
    echo Node.js가 설치되어 있는지 확인해주세요. (https://nodejs.org)
    pause
    exit /b
)
echo ✅ 설치 완료.

echo.
echo [2] Frontend 서버 실행 중 (npm run dev)...
echo 브라우저에서 http://localhost:5173 으로 접속하세요.
npm run dev

pause
