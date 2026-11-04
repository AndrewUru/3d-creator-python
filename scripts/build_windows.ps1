$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Falta .venv. Ejecuta: py -3.12 -m venv .venv" }
& $python -m pip install -r requirements.txt -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion" }
$flags = @("--noconfirm", "--clean", "--onedir", "--console", "--name", "3D-Creator", "--collect-all", "gradio", "--collect-all", "gradio_client", "--collect-all", "trimesh", "--collect-all", "shapely", "--collect-all", "cv2", "--collect-all", "manifold3d", "--collect-submodules", "webview", "--hidden-import=uvicorn.protocols.http.auto", "--hidden-import=uvicorn.lifespan.on", "desktop.py")
& $python -m PyInstaller @flags
if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion" }
& ".\dist\3D-Creator\3D-Creator.exe" --check
if ($LASTEXITCODE -ne 0) { throw "Fallo la comprobacion del ejecutable" }
Write-Host "Compilado: dist\3D-Creator\3D-Creator.exe"
