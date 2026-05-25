# Watchface Modding Helper Script
param(
    [string]$Watchface = "",
    [string]$Action = "",
    [switch]$Release = $false,
    [string]$KsPass = "",
    [string]$KeyPass = ""
)

$toolsDir = Join-Path $PSScriptRoot "tools"
$scriptDir = $PSScriptRoot

if (-not (Test-Path "$toolsDir\apktool.jar")) {
    Write-Host "Error: apktool.jar not found in $toolsDir" -ForegroundColor Red
    exit 1
}

function Decompile {
    param([string]$ApkPath, [string]$OutDir)
    Write-Host "Decompiling $ApkPath to $OutDir..." -ForegroundColor Cyan
    if (Test-Path $OutDir) {
        Remove-Item -Recurse -Force $OutDir
    }
    java -jar "$toolsDir\apktool.jar" d "$ApkPath" -o "$OutDir" -f
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Decompilation complete." -ForegroundColor Green
    } else {
        Write-Host "Decompilation failed!" -ForegroundColor Red
        exit 1
    }
}

function Build {
    param([string]$InDir, [string]$OutApk)
    Write-Host "Building APK from $InDir..." -ForegroundColor Cyan
    java -jar "$toolsDir\apktool.jar" b "$InDir" -o "$OutApk"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Build succeeded: $OutApk" -ForegroundColor Green
}

function Ensure-ReleaseKeystore {
    $ksPath = Join-Path $scriptDir "release-key.jks"
    if (-not (Test-Path $ksPath)) {
        Write-Host "release-key.jks not found. Generating a new one..." -ForegroundColor Yellow
        & "C:\Program Files\Java\jre1.8.0_491\bin\keytool.exe" -genkey -v -keystore "$ksPath" -keyalg RSA -keysize 2048 -validity 10000 -alias WatchfaceKey -storepass watchface2026 -keypass watchface2026 -dname "CN=WatchfaceEditor, OU=Modding, O=WatchfaceEditor, L=Unknown, ST=Unknown, C=US" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Generated release-key.jks" -ForegroundColor Green
        } else {
            Write-Host "Failed to generate keystore!" -ForegroundColor Red
            return $null
        }
    }
    return $ksPath
}

function Sign-Apk {
    param([string]$ApkPath)
    $alignedPath = [System.IO.Path]::GetDirectoryName($ApkPath) + "\" + [System.IO.Path]::GetFileNameWithoutExtension($ApkPath) + "_aligned.apk"
    Write-Host "Aligning APK (4-byte boundary)..." -ForegroundColor Cyan
    & "C:\RSL\build-tools\34.0.0\zipalign.exe" -f -p -v 4 "$ApkPath" "$alignedPath" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "zipalign failed!" -ForegroundColor Red
        exit 1
    }
    Move-Item -Force "$alignedPath" "$ApkPath"

    $ksPath = Ensure-ReleaseKeystore
    if (-not $ksPath) {
        Write-Host "No keystore found, cannot sign!" -ForegroundColor Red
        exit 1
    }
    $ksPassArg = if ($KsPass) { "--ks-pass pass:$KsPass" } else { "--ks-pass pass:watchface2026" }
    $keyPassArg = if ($KeyPass) { "--key-pass pass:$KeyPass" } else { "--key-pass pass:watchface2026" }
    Write-Host "Signing..." -ForegroundColor Cyan
    java -jar "$toolsDir\apksigner.jar" sign --ks "$ksPath" --ks-key-alias WatchfaceKey $ksPassArg $keyPassArg "$ApkPath"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Signing complete." -ForegroundColor Green
    } else {
        Write-Host "Signing failed!" -ForegroundColor Red
        exit 1
    }
}

function Verify-Apk {
    param([string]$ApkPath)
    Write-Host "Verifying signature..." -ForegroundColor Cyan
    java -jar "$toolsDir\apksigner.jar" verify --verbose $ApkPath 2>&1
}

function SetupWatchface {
    param([string]$Name)
    $zipFile = Join-Path $scriptDir "$Name.zip"
    $extractDir = Join-Path $scriptDir "${Name}_extracted"

    if (-not (Test-Path $zipFile)) {
        $zipFile = Get-ChildItem -Path $scriptDir -Filter "*$Name*.zip" | Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $zipFile -or -not (Test-Path $zipFile)) {
        Write-Host "Error: Could not find $Name.zip" -ForegroundColor Red
        return $false
    }

    Write-Host "Extracting $zipFile..." -ForegroundColor Cyan
    if (Test-Path $extractDir) {
        Remove-Item -Recurse -Force $extractDir
    }
    Expand-Archive -LiteralPath $zipFile -DestinationPath $extractDir -Force

    $baseApk = Join-Path $extractDir "base.apk"
    if (-not (Test-Path $baseApk)) {
        Write-Host "Error: base.apk not found in extracted files" -ForegroundColor Red
        return $false
    }

    $workDir = Join-Path $scriptDir $Name
    Decompile -ApkPath $baseApk -OutDir $workDir
    return $true
}

# --- Main ---
if (-not $Action -or -not $Watchface) {
    Write-Host "Usage: .\mod_helper.ps1 -Watchface <name> -Action <prepare|build>" -ForegroundColor Yellow
    Write-Host "  prepare    Decompile, scan, generate tint_config.json"
    Write-Host "  build      Apply mod, build APK, sign, verify"
    Write-Host "  build -Release  Build and sign with release key"
    exit
}

if ($Action -eq "prepare") {
    if (-not (SetupWatchface -Name $Watchface)) { exit 1 }
    python "$scriptDir\scan_tintable.py" --watchface "$Watchface"
    python "$scriptDir\smart_modder.py" --watchface "$Watchface" --auto-background --generate-only
    Write-Host "`n=== Ready ===" -ForegroundColor Green
    Write-Host "Edit $Watchface\tint_config.json to configure colors, then run:" -ForegroundColor White
    Write-Host "  .\mod_helper.ps1 -Watchface $Watchface -Action build" -ForegroundColor Cyan
    exit
}

if ($Action -eq "build") {
    python "$scriptDir\smart_modder.py" --watchface "$Watchface"
    $workDir = Join-Path $scriptDir $Watchface
    $outApk = Join-Path $scriptDir "${Watchface}_modded.apk"
    Build -InDir $workDir -OutApk $outApk
    Sign-Apk -ApkPath $outApk
    Verify-Apk -ApkPath $outApk
    Write-Host "`n=== Done ===" -ForegroundColor Green
    Write-Host "APK: $outApk" -ForegroundColor Cyan
    exit
}

Write-Host "Unknown action: $Action. Use 'prepare' or 'build'." -ForegroundColor Red
exit 1
