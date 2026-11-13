$ErrorActionPreference = "Stop"

# Fixed build/dist directories. Run from any current working directory.
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$distDir = Join-Path $root "dist\MelodyNotation"
$exe = Join-Path $distDir "MelodyNotation.exe"

Push-Location $root
try {
    Write-Host "=== Melody Notation v0.5.10 Build ===" -ForegroundColor Cyan

    # Refuse to package stale GUI sample imports. This was the source of the
    # original 'No module named melody_notation' popup in the frozen src build.
    $sampleFiles = @(
        (Join-Path $root "src\gui.py"),
        (Join-Path $root "src\qt_gui.py"),
        (Join-Path $root "src\workspace_gui.py")
    )
    foreach ($file in $sampleFiles) {
        if (-not (Test-Path -LiteralPath $file)) {
            throw "Missing source file: $file"
        }
        $old = Select-String -LiteralPath $file -Pattern 'resources\.files\(\s*["'']melody_notation["'']\s*\)'
        if ($old) {
            throw "Old sample resource reference remains in ${file}:$($old[0].LineNumber). Apply the src/ patch before building."
        }
    }

    # Stop only the executable from *this* release folder, not arbitrary
    # processes with the same name in other installations.
    Get-Process -Name "MelodyNotation" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            if ($_.Path -and ($_.Path -ieq $exe)) {
                Write-Host "Stopping running MelodyNotation.exe (PID $($_.Id))..."
                Stop-Process -Id $_.Id -Force -ErrorAction Stop
                $_.WaitForExit(5000) | Out-Null
            }
        } catch {
            Write-Warning "Unable to stop MelodyNotation.exe: $_"
        }
    }

    # Old compiled files must not survive a successful new build.
    # Retry briefly for transient Windows DLL/AV locks, but keep paths fixed.
    if (Test-Path -LiteralPath $distDir) {
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            try {
                Remove-Item -LiteralPath $distDir -Recurse -Force -ErrorAction Stop
                break
            } catch {
                if ($attempt -eq 5) {
                    throw "Could not remove old dist folder ($distDir). Close old EXE/Explorer previews or check file locks. Last error: $_"
                }
                Start-Sleep -Seconds 2
            }
        }
    }

    # Reuse standard build/ and dist/ directories, no per-build folder names.
    python -m PyInstaller `
        --noconfirm `
        --onedir `
        --console `
        --name "MelodyNotation" `
        --paths "$root" `
        --collect-all src `
        --workpath "$root\build" `
        --distpath "$root\dist" `
        --specpath "$root" `
        packaging/gui_entry.py

    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed, exit code $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $exe)) { throw "EXE missing after build: $exe" }

    # Self-test must run from the newly built EXE, not the source environment.
    Write-Host "Verifying frozen package and embedded examples..." -ForegroundColor Cyan
    & $exe --verify-package
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged EXE failed sample/GUI verification (exit code $LASTEXITCODE)"
    }

    Write-Host "BUILD + PACKAGE VERIFICATION PASSED" -ForegroundColor Green
    Write-Host "Output: $exe"
} finally {
    Pop-Location
}
