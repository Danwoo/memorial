@echo off
chcp 65001 > nul
echo ===================================================
echo   Memoir AI - Environment Reset
echo ===================================================
echo.

echo [1] 종료되지 않은 프로세스 강제 종료 중...
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM uvicorn.exe > nul 2>&1
echo ✅ 프로세스 정리 완료.

echo.
echo [2] 손상된 가상환경(.venv) 제거 중...
if exist backend\.venv (
    rmdir /s /q backend\.venv
)
if exist backend\.venv (
    echo ❌ 폴더 삭제 실패. 파일이 사용 중입니다. 재부팅이 필요할 수 있습니다.
    pause
    exit /b
)
echo ✅ 가상환경 제거 완료.

echo.
echo [3] 가상환경 재생성 및 라이브러리 설치 (OneDrive 호환 모드)...
cd backend
call uv sync --link-mode=copy
if %errorlevel% neq 0 (
    echo ❌ 설치 실패.
    pause
    exit /b
)
echo ✅ 설치 완료!

echo.
echo [4] 최종 연결 테스트...
.venv\Scripts\python.exe check_integration.py

echo.
pause
