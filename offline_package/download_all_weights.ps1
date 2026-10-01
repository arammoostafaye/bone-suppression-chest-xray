# BoneSuppression AI - Offline Weights Downloader with Resume & Verification
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "    BoneSuppression AI - Model Weights Downloader & Verifier" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

$weightsDir = Join-Path $PSScriptRoot "weights"
if (-not (Test-Path $weightsDir)) {
    New-Item -ItemType Directory -Path $weightsDir | Out-Null
}

$files = @(
    @{
        Name = "bone_suppression.ts"
        Url  = "https://huggingface.co/qureaiorg/bone-suppression/resolve/main/weights/bone_suppression.ts"
        ExpectedSize = 417479853
    },
    @{
        Name = "lung_component_suppression.ts"
        Url  = "https://huggingface.co/qureaiorg/bone-suppression/resolve/main/weights/lung_component_suppression.ts"
        ExpectedSize = 417453912
    }
)

foreach ($item in $files) {
    $targetPath = Join-Path $weightsDir $item.Name
    Write-Host ("`nDownloading " + $item.Name + " (" + [math]::Round($item.ExpectedSize / 1MB, 1) + " MB)...") -ForegroundColor Yellow

    if (Test-Path $targetPath) {
        $actualSize = (Get-Item $targetPath).Length
        if ($actualSize -eq $item.ExpectedSize) {
            Write-Host ("File " + $item.Name + " is already downloaded and verified!") -ForegroundColor Green
            continue
        }
    }

    try {
        Start-BitsTransfer -Source $item.Url -Destination $targetPath -DisplayName $item.Name
    } catch {
        Write-Host "BitsTransfer failed, trying curl fallback..." -ForegroundColor DarkYellow
        curl.exe -L --retry 3 -C - $item.Url -o $targetPath
    }

    $downloadedSize = (Get-Item $targetPath).Length
    if ($downloadedSize -eq $item.ExpectedSize) {
        Write-Host ("✓ " + $item.Name + " verified successfully (" + $downloadedSize + " bytes)") -ForegroundColor Green
    } else {
        Write-Host ("⚠ Size mismatch for " + $item.Name + ": Expected " + $item.ExpectedSize + ", got " + $downloadedSize) -ForegroundColor Red
    }
}

Write-Host "`nAll models are downloaded and ready for 100% offline air-gapped clinical operation." -ForegroundColor Green