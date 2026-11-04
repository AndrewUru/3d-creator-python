# 3D Creator Studio · Ejecutable para Windows

Este paquete es una **primera versión portable** para Windows 10/11 x64. Abre la interfaz Gradio en una ventana nativa mediante pywebview y Microsoft Edge WebView2. El servidor permanece en `127.0.0.1` y se cierra con la ventana.

## Descargar desde GitHub Actions

1. En GitHub, abre **Actions → Windows portable**.
2. Ejecuta `Run workflow` desde la rama de desarrollo o consulta una ejecución completada.
3. Si los pasos de compilación y pruebas terminan correctamente, descarga **3D-Creator-Windows-x64** en **Artifacts**.
4. Descomprime *toda* la carpeta y abre `3D-Creator.exe` con doble clic. **No muevas solo el EXE**: necesita la carpeta `_internal`.

No tienes que instalar Python ni abrir VS Code en el ordenador que ejecute el paquete. La compilación necesita Windows y Python 3.12.

## Compilar en tu ordenador (PowerShell)

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-desktop.txt
.\.venv\Scripts\python -m PyInstaller --clean --noconfirm packaging/windows.spec
& ".\dist\3D-Creator\3D-Creator.exe" --smoke-test
```

El resultado está en `dist/3D-Creator/`. Para desarrollar la ventana sin compilar:

```powershell
.\.venv\Scripts\python desktop.py
```

## Qué funciona en la versión portable inicial

- **Dar volumen:** siluetas, letras y dibujos; exportación a STL/GLB.
- **Relieve → Mapa de alturas:** funciona sin inferencia de IA.
- **Visores 3D y descargas:** incluidos en la interfaz existente.

**Aún no están incluidos los entornos ni los pesos de IA.** Las modalidades **Objeto completo (TripoSR)** y **Relieve → Fotografía IA (Depth Anything)** necesitan por ahora la instalación Python documentada en el README. No basta con copiar una carpeta `.venv-tripo` o `.venv-ai` al lado del EXE, porque sus dependencias y rutas no son necesariamente relocatables.

## Requisitos y problemas habituales

- Windows 10/11 x64 con **Microsoft Edge WebView2 Runtime** y un runtime .NET compatible con pywebview; en algunos sistemas puede requerir instalación por separado.
- No se requiere conexión a Internet para las operaciones sin IA una vez descargado el paquete.
- Archivos temporales de Gradio en `%LOCALAPPDATA%\Imagen-a-3D\gradio-cache`.
- Diagnóstico del arranque en `%LOCALAPPDATA%\Imagen-a-3D\desktop.log`.
- Si la ventana no se abre, revisa `desktop.log` y verifica WebView2.
- El ejecutable no se firma digitalmente: Windows SmartScreen puede advertir de aplicaciones sin firma. No desactives la protección del sistema.
- El paso `--smoke-test` comprueba que el servidor HTTP empaquetado responde; **no sustituye** la prueba visual/manual de WebView2, generación y exportación.

## Próximas mejoras

Distribuir los modelos de IA y sus runtimes locales de forma separada, crear un instalador con acceso directo y desinstalador, añadir iconos propios y pruebas de interfaz de escritorio.
