@echo off
echo ============================================================
echo Instagram Reels Poster - First Time Setup
echo ============================================================
echo.
echo This script will:
echo 1. Create your .env file
echo 2. Generate all required security keys
echo 3. Set up the environment
echo.
pause
echo.

REM Check if .env already exists
if exist ".env" (
    echo.
    echo WARNING: .env file already exists!
    echo.
    choice /C YN /M "Do you want to overwrite it"
    if errorlevel 2 goto :EOF
    echo.
    echo Backing up existing .env to .env.backup
    copy .env .env.backup >nul
)

echo Creating .env file...
echo.

REM Generate ENCRYPTION_KEY
echo [1/4] Generating ENCRYPTION_KEY...
for /f "delims=" %%i in ('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"') do set ENCRYPTION_KEY=%%i
echo Generated: %ENCRYPTION_KEY:~0,20%...

REM Generate DEVICE_SALT
echo [2/4] Generating DEVICE_SALT...
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set DEVICE_SALT=%%i
echo Generated: %DEVICE_SALT:~0,20%...

REM Generate SECRET_KEY
echo [3/4] Generating SECRET_KEY...
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SECRET_KEY=%%i
echo Generated: %SECRET_KEY:~0,20%...

REM Generate API_KEY
echo [4/4] Generating API_KEY...
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set API_KEY=%%i
echo Generated: %API_KEY:~0,20%...

echo.
echo Writing to .env file...

REM Create .env file
(
echo # ============================================
echo # REQUIRED ENVIRONMENT VARIABLES
echo # ============================================
echo # Generated on %date% at %time%
echo.
echo # API Key for authenticating requests
echo API_KEY=%API_KEY%
echo.
echo # Encryption key for storing Instagram passwords
echo # WARNING: Never change this - you'll lose access to encrypted passwords
echo ENCRYPTION_KEY=%ENCRYPTION_KEY%
echo.
echo # Device fingerprint salt
echo # CRITICAL: NEVER CHANGE THIS IN PRODUCTION
echo # Changing this will invalidate ALL Instagram sessions
echo DEVICE_SALT=%DEVICE_SALT%
echo.
echo # Flask secret key for session management
echo SECRET_KEY=%SECRET_KEY%
echo.
echo # ============================================
echo # OPTIONAL CONFIGURATION
echo # ============================================
echo.
echo # Database URL ^(defaults to SQLite if not set^)
echo # DATABASE_URL=sqlite:///reels_poster.db
echo.
echo # Redis URL for rate limiting ^(optional^)
echo # REDIS_URL=redis://localhost:6379/0
echo.
echo # Upload folder ^(defaults to ./uploads^)
echo # UPLOAD_FOLDER=uploads
) > .env

echo.
echo ============================================================
echo ✅ Setup Complete!
echo ============================================================
echo.
echo Your .env file has been created with these keys:
echo.
echo API_KEY: %API_KEY:~0,20%...
echo ENCRYPTION_KEY: %ENCRYPTION_KEY:~0,20%...
echo DEVICE_SALT: %DEVICE_SALT:~0,20%...
echo SECRET_KEY: %SECRET_KEY:~0,20%...
echo.
echo ⚠️  IMPORTANT SECURITY WARNINGS:
echo ============================================
echo 1. NEVER commit .env to git
echo 2. NEVER change DEVICE_SALT after first use
echo 3. Keep .env file secure - it contains secrets
echo 4. Backup .env file in a secure location
echo ============================================
echo.
echo Next steps:
echo 1. Run: python check_setup.py   ^(verify setup^)
echo 2. Run: python create_session.py ^(create Instagram sessions^)
echo 3. Run: python app.py            ^(start the application^)
echo.
pause
