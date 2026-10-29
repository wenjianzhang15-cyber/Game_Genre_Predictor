$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed with exit code $LASTEXITCODE" }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker is not installed. Install and start Docker Desktop with a Linux container backend first.'
}
Push-Location $projectRoot
$containerName = 'genre-verify-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$created = $false
try {
    Invoke-Docker info --format '{{.OSType}}'
    Invoke-Docker build --target verification -t game-genre-predictor:verify .
    Invoke-Docker run --rm --read-only --tmpfs '/tmp:rw,noexec,nosuid,size=64m' --memory 1g --cpus 2 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges game-genre-predictor:verify
    Invoke-Docker build --target production -t game-genre-predictor:local .
    Invoke-Docker run -d --name $containerName --read-only --tmpfs '/tmp:rw,noexec,nosuid,size=64m' --memory 1g --cpus 2 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges -p 127.0.0.1::7860 game-genre-predictor:local
    $created = $true
    $binding = (& docker port $containerName 7860/tcp).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not discover local container port.' }
    $baseUrl = 'http://' + $binding
    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-RestMethod "$baseUrl/health" -TimeoutSec 2
            if ($health.ok) { $healthy = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $healthy) { throw 'Container health check did not become ready.' }
    $prediction = Invoke-RestMethod "$baseUrl/predict" -Method Post -ContentType 'application/json' -Body '{"url":"/ui/covers/HollowKnight.jpg"}' -TimeoutSec 20
    if ($prediction.label -ne 'platform') { throw 'Unexpected real-model prediction.' }
    Invoke-Docker exec $containerName python -c 'import os; assert os.getuid() == 1000; assert not os.path.exists("/app/.git"); assert not os.path.exists("/app/tests")'
    Write-Output 'Docker tests, non-root/read-only runtime, health check and real-model inference passed.'
} finally {
    if ($created) { & docker rm -f $containerName | Out-Null }
    Pop-Location
}
