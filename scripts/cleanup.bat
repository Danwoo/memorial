@echo off
chcp 65001 > nul
echo ===================================================
echo   프로젝트 파일 정리
echo ===================================================
echo.

echo [1/3] MD 파일들을 docs 폴더로 이동...
if exist API_Spec.md move API_Spec.md docs\
if exist Agent_Architecture.md move Agent_Architecture.md docs\
if exist Agent_Design_Spec.md move Agent_Design_Spec.md docs\
if exist Data_Schema.md move Data_Schema.md docs\
if exist PRD.md move PRD.md docs\
if exist Project_Structure.md move Project_Structure.md docs\
if exist Tech_Spec.md move Tech_Spec.md docs\
echo    완료!

echo [2/3] BAT 파일들을 scripts 폴더로 이동...
if not exist scripts mkdir scripts
if exist fix_and_run.bat move fix_and_run.bat scripts\
if exist fix_lock_and_sync.bat move fix_lock_and_sync.bat scripts\
if exist reset_env.bat move reset_env.bat scripts\
if exist start_all.bat move start_all.bat scripts\
if exist test_backend.bat move test_backend.bat scripts\
if exist verify_phase2.bat move verify_phase2.bat scripts\
echo    완료!

echo [3/3] 정리 스크립트 자체를 scripts로 이동...
move cleanup.bat scripts\ 2>nul

echo.
echo ===================================================
echo ✅ 정리 완료! 이제 memorial 폴더에는:
echo    - backend/
echo    - docs/
echo    - extension/
echo    - frontend/
echo    - scripts/
echo    - .env.example
echo    - README.md
echo ===================================================
pause
