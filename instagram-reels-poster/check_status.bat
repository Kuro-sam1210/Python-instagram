@echo off
echo ============================================================
echo Check Application Status
echo ============================================================
echo.

powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:5000/health' -Method Get; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'APPLICATION STATUS' -ForegroundColor Green; Write-Host '============================================================' -ForegroundColor Green; Write-Host ''; Write-Host 'Overall Status:' $response.status; Write-Host 'Database:' $response.database; Write-Host 'Scheduler:' $response.scheduler; Write-Host 'Pending Jobs:' $response.pending_jobs; Write-Host 'Timestamp:' $response.timestamp; Write-Host ''; if ($response.status -eq 'healthy') { Write-Host '✓ Application is running normally' -ForegroundColor Green } else { Write-Host '✗ Application has issues' -ForegroundColor Yellow } } catch { Write-Host '============================================================' -ForegroundColor Red; Write-Host 'ERROR: Cannot connect to application' -ForegroundColor Red; Write-Host '============================================================' -ForegroundColor Red; Write-Host ''; Write-Host 'Is the app running?' -ForegroundColor Yellow; Write-Host 'Start it with: python app.py' -ForegroundColor Yellow; Write-Host 'Or double-click: start_app.bat' -ForegroundColor Yellow }"

echo.
echo.
pause
