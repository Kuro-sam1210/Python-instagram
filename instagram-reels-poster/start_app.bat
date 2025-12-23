@echo off
echo ============================================================
echo Instagram Reels Poster - Starting...
echo ============================================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Running app.py...
echo.

python app.py

echo.
echo ============================================================
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ App exited with error code: %ERRORLEVEL%
    echo Check the error messages above
) else (
    echo ✅ App stopped normally
)
echo ============================================================
echo.
pause
