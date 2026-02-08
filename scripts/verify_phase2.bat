@echo off
chcp 65001 > nul
echo ==============================================
echo      Memoir AI - Phase 2 Verification
echo ==============================================
echo.

:: 1. Backend Server Check
echo [1] Checking Backend Server Status...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 8000 | Select-Object -ExpandProperty TcpTestSucceeded" > server_status.tmp
set /p server_running=<server_status.tmp
del server_status.tmp

if "%server_running%"=="True" (
    echo ✅ Backend Server is ALREADY RUNNING.
) else (
    echo ⚠️ Backend Server is NOT running.
    echo 🚀 Starting Backend Server in a new window...
    start "Memoir AI Backend" cmd /k "cd backend && .venv\Scripts\uvicorn.exe app.main:app --reload"
    echo Waiting 10 seconds for server startup...
    timeout /t 10 > nul
)

:: 2. Run Integration Check (Simple)
echo.
echo [2] Checking System Connections (OpenAI, Supabase, Neo4j)...
echo.

cd backend
.venv\Scripts\python.exe check_integration.py
echo.
echo If you see check marks above, connections are working!
pause

if exist phase2_test_result.txt (
    echo.
    echo ================= TEST RESULTS =================
    type phase2_test_result.txt
    echo ================================================
) else (
    echo ❌ Test Script Failed to produce output.
    echo Please check python installation and path.
)

echo.
echo [3] Verification Complete.
echo You can now check the Frontend at: http://localhost:5173
echo.
echo Press any key to close this window...
pause
exit /b
