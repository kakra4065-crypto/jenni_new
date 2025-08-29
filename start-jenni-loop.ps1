# === CONFIG ===
$jenniDir     = "$env:USERPROFILE\Desktop\jenni_new"
$cloudflared  = "$env:USERPROFILE\Desktop\cloudflared.exe"
$flaskCommand = "flask run --host=0.0.0.0 --port=5000"
$tunnelName   = "divinebrain-tunnel"

# === FUNCTIONS ===
function Test-Internet {
    try {
        $null = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 5
        return $true
    } catch {
        return $false
    }
}

Write-Host "[Start] Monitoring app and tunnel..." -ForegroundColor Cyan

while ($true) {
    if (-not (Test-Internet)) {
        Write-Warning "No internet connection. Retrying in 10 seconds..."
        Start-Sleep -Seconds 10
        continue
    }

    Write-Host "[Info] Starting Flask and Cloudflared..." -ForegroundColor Yellow

    # Start Flask app (background)
    $flaskJob = Start-Job -ScriptBlock {
        cd $using:jenniDir
        $env:FLASK_APP = 'app.py'
        $env:FLASK_ENV = 'production'
        flask run --host=0.0.0.0 --port=5000
    }

    # Start cloudflared tunnel (background)
    $tunnelJob = Start-Job -ScriptBlock {
        cd $using:jenniDir
        & $using:cloudflared tunnel run $using:tunnelName
    }

    # Wait for either job to crash
    while ($true) {
        Start-Sleep -Seconds 3
        if ($flaskJob.State -ne 'Running' -or $tunnelJob.State -ne 'Running') {
            Write-Host "[Error] One of the processes stopped. Restarting in 5 seconds..." -ForegroundColor Red
            Stop-Job $flaskJob -Force
            Stop-Job $tunnelJob -Force
            Remove-Job $flaskJob, $tunnelJob -Force
            Start-Sleep -Seconds 5
            break
        }
    }
}
