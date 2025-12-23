@echo off
echo ============================================================
echo List All Instagram Accounts
echo ============================================================
echo.

REM Load API_KEY from .env
for /f "tokens=1,2 delims==" %%a in ('findstr "^API_KEY=" .env') do set API_KEY=%%b

if "%API_KEY%"=="" (
    echo ERROR: API_KEY not found in .env file
    pause
    exit /b 1
)

echo Fetching accounts...
echo.

powershell -Command "$headers = @{'X-API-Key'='%API_KEY%'}; try { $response = Invoke-RestMethod -Uri 'http://localhost:5000/api/accounts' -Method Get -Headers $headers; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'ACCOUNTS:' -ForegroundColor Green; Write-Host '============================================================' -ForegroundColor Green; if ($response.Count -eq 0) { Write-Host 'No accounts found. Add one using add_account.bat' } else { $response | ForEach-Object { Write-Host ''; Write-Host 'ID:' $_.id; Write-Host 'Username:' $_.username; Write-Host 'Active:' $_.is_active; Write-Host 'Created:' $_.created_at; Write-Host 'Posts:' $_.post_count; Write-Host '---' } } } catch { Write-Host '============================================================' -ForegroundColor Red; Write-Host 'ERROR:' $_.Exception.Message -ForegroundColor Red; Write-Host '============================================================' -ForegroundColor Red }"

echo.
pause
