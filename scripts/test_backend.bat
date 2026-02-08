@echo off
chcp 65001 > nul
echo ===================================================
echo   Backend 테스트 (오류 메시지 확인용)
echo ===================================================
cd backend

echo.
echo [1] sniffio 모듈 테스트...
.venv\Scripts\python -c "import sniffio; print('✅ sniffio OK')"
if %errorlevel% neq 0 (
    echo ❌ sniffio 없음. 설치 시도...
    .venv\Scripts\pip install sniffio
)

echo.
echo [2] uvicorn 직접 실행 (오류가 나면 여기서 멈춤)...
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo 서버가 종료되었습니다.
pause
