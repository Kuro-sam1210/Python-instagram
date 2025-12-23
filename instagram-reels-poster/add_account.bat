@echo off
echo ============================================================
echo Add Instagram Account to Database
echo ============================================================
echo.

REM Load API_KEY from .env
for /f "tokens=1,2 delims==" %%a in ('findstr "^API_KEY=" .env') do set API_KEY=%%b

if "%API_KEY%"=="" (
    echo ERROR: API_KEY not found in .env file
    echo Make sure .env file exists and contains API_KEY
    pause
    exit /b 1
)

echo Using API_KEY: %API_KEY:~0,20%...
echo.

REM Get Instagram credentials
set /p USERNAME="Enter Instagram username: "
set /p PASSWORD="Enter Instagram password: "

echo.
echo Adding account to database...
echo.

REM Make the API request using PowerShell (more reliable than curl on Windows)
powershell -Command "$headers = @{'X-API-Key'='%API_KEY%'; 'Content-Type'='application/json'}; $body = @{username='%USERNAME%'; password='%PASSWORD%'; is_active=$true} | ConvertTo-Json; try { $response = Invoke-RestMethod -Uri 'http://localhost:5000/api/accounts' -Method Post -Headers $headers -Body $body; Write-Host ''; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'SUCCESS! Account added' -ForegroundColor Green; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'Account ID:' $response.id; Write-Host 'Message:' $response.message } catch { Write-Host ''; Write-Host '============================================================' -ForegroundColor Red; Write-Host 'ERROR:' $_.Exception.Message -ForegroundColor Red; Write-Host '============================================================' -ForegroundColor Red; if ($_.Exception.Response) { $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); $reader.BaseStream.Position = 0; $responseBody = $reader.ReadToEnd(); Write-Host 'Details:' $responseBody } }"

echo.
echo.
pause
