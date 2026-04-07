@echo off
echo ============================================
echo   AgentHive - Multi-Agent Document Intelligence
echo ============================================
echo.

echo Starting backend server on port 8000...
start "AgentHive-Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak > nul

echo Starting frontend server on port 5173...
start "AgentHive-Frontend" cmd /c "cd /d %~dp0frontend && npx vite --port 5173"

echo.
echo ============================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Both servers are starting in separate windows.
echo Press any key to exit this launcher...
pause > nul
