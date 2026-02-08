@echo off
chcp 65001 > nul
echo ===================================================
echo   Memoir AI - Dependency Fix & Verify
echo ===================================================
echo.

echo [1] 실행 중인 Python/Server 프로세스 정리 중...
echo (파일 잠금 오류 "Access Denied" 해결을 위해 필수)
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM uvicorn.exe > nul 2>&1
echo ✅ 프로세스 정리 완료.

echo.
echo [2] 라이브러리 동기화 재시도 (uv sync)...
cd backend
call uv sync
if %errorlevel% neq 0 (
    echo ❌ 동기화 실패. 관리자 권한으로 실행했는지 확인해주세요.
    pause
    exit /b
)
echo ✅ 기본 동기화 완료.

echo [2-1] 손상된 라이브러리 강제 복구 (Force Reinstall)...
call uv pip install --force-reinstall jsonpointer langchain-core langchain-openai sniffio
echo ✅ 복구 완료.

echo.
echo [3] 최종 연결 테스트 (Check Integration)...
.venv\Scripts\python.exe check_integration.py

echo.
echo ===================================================
echo 모든 항목에 체크표시(✅)가 뜨면 준비 끝입니다.
echo ===================================================
pause
