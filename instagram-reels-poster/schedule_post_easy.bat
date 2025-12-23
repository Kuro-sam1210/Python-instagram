@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo Schedule Instagram Post (Timezone-Aware)
echo ============================================================
echo.

REM Load API_KEY from .env
for /f "tokens=1,2 delims==" %%a in ('findstr "^API_KEY=" .env') do set API_KEY=%%b

if "!API_KEY!"=="" (
    echo ERROR: API_KEY not found in .env file
    pause
    exit /b 1
)

echo Your current local time is:
powershell -Command "Write-Host (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') -ForegroundColor Cyan"
echo.

REM Get inputs
set /p ACCOUNT_ID="Enter Account ID (1 for top_anime_king): "
set /p VIDEO_PATH="Drag and drop video file here: "
set VIDEO_PATH=!VIDEO_PATH:"=!

set /p CAPTION="Enter caption: "
set /p HASHTAGS="Enter hashtags: "

echo.
echo Enter the time you want to post in YOUR LOCAL TIME (not UTC)
echo Format: YYYY-MM-DD HH:MM  (24-hour format)
echo Example: 2025-12-22 23:30
set /p LOCAL_TIME="Local time to post: "

echo.
echo Processing...

REM Use PowerShell to convert and schedule
powershell -Command "$ErrorActionPreference='Stop'; try { $apiKey='!API_KEY!'; $accountId='!ACCOUNT_ID!'; $videoPath='!VIDEO_PATH!'; $caption='!CAPTION!'; $hashtags='!HASHTAGS!'; $localTimeStr='!LOCAL_TIME!'; $localTime=[DateTime]::ParseExact($localTimeStr,'yyyy-MM-dd HH:mm',$null,[System.Globalization.DateTimeStyles]::AssumeLocal); $utcTime=$localTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'); Write-Host ''; Write-Host 'Conversion:' -ForegroundColor Yellow; Write-Host '  Your local time: ' -NoNewline; Write-Host $localTime.ToString('yyyy-MM-dd HH:mm:ss') -ForegroundColor Cyan; Write-Host '  UTC time:        ' -NoNewline; Write-Host $utcTime -ForegroundColor Green; Write-Host ''; Write-Host 'Uploading to server...' -ForegroundColor Yellow; $boundary=[Guid]::NewGuid().ToString(); $LF=\"`r`n\"; $fileBytes=[IO.File]::ReadAllBytes($videoPath); $fileName=[IO.Path]::GetFileName($videoPath); $bodyLines=@(\"--$boundary\",\"Content-Disposition: form-data; name=`\"accountId`\"\",\"\",$accountId,\"--$boundary\",\"Content-Disposition: form-data; name=`\"caption`\"\",\"\",$caption,\"--$boundary\",\"Content-Disposition: form-data; name=`\"hashtags`\"\",\"\",$hashtags,\"--$boundary\",\"Content-Disposition: form-data; name=`\"scheduledTime`\"\",\"\",$utcTime,\"--$boundary\",\"Content-Disposition: form-data; name=`\"videoFile`\"; filename=`\"$fileName`\"\",\"Content-Type: video/mp4\",\"\"); $bodyText=($bodyLines -join $LF)+$LF; $bodyBytes=[Text.Encoding]::UTF8.GetBytes($bodyText)+$fileBytes+[Text.Encoding]::UTF8.GetBytes(\"$LF--$boundary--$LF\"); $headers=@{'X-API-Key'=$apiKey;'Content-Type'=\"multipart/form-data; boundary=$boundary\"}; $response=Invoke-RestMethod -Uri 'http://localhost:5000/api/posts' -Method Post -Headers $headers -Body $bodyBytes; Write-Host ''; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'SUCCESS! Post scheduled' -ForegroundColor Green; Write-Host '============================================================' -ForegroundColor Green; Write-Host 'Post ID: ' -NoNewline; Write-Host $response.id -ForegroundColor Cyan; Write-Host 'Will post at your local time: ' -NoNewline; Write-Host $localTime.ToString('yyyy-MM-dd HH:mm:ss') -ForegroundColor Cyan; } catch { Write-Host ''; Write-Host '============================================================' -ForegroundColor Red; Write-Host 'ERROR' -ForegroundColor Red; Write-Host '============================================================' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; if($_.Exception.Response) { $reader=New-Object IO.StreamReader($_.Exception.Response.GetResponseStream()); $reader.BaseStream.Position=0; Write-Host $reader.ReadToEnd() -ForegroundColor Red; } }"

echo.
pause