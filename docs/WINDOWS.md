# Ejecutable portable de Windows

Esta es una **versión preliminar** del empaquetado de 3D Creator Studio.
No se han cambiado los motores de generación ni el flujo Python habitual.

## Descargar la compilación

Abre la pestaña **Actions** de GitHub, selecciona **Windows portable EXE**
y ejecuta **Run workflow** sobre la rama `feat/windows-portable-exe`.
Cuando termine correctamente, descarga el artefacto
`3D-Creator-Windows-x64`. Extrae el ZIP y abre
`3D-Creator/3D-Creator.exe`.

**Conserva toda la carpeta**, incluido `_internal`; el ejecutable no
funciona si se separa de sus dependencias.

## Compilar en Windows 10/11

Requiere Python 3.12 de 64 bits para compilar:

```powershell
py -3.12 -m venv .venv
.\scripts\build_windows.ps1
```

El resultado queda en `dist/3D-Creator/3D-Creator.exe`.
El script comprueba que el EXE puede importar las dependencias y construir
la interfaz, pero se debe realizar además una prueba manual de la ventana,
el visor 3D y las exportaciones STL/GLB en Windows.

## Comportamiento

- Gradio escucha únicamente en `127.0.0.1:7860`, sin enlaces públicos.
- pywebview muestra la interfaz en una ventana propia usando WebView2.
- Si pywebview falla, intenta abrir el navegador predeterminado.
- Cerrar la ventana nativa detiene el servidor. Con el navegador alternativo,
  pulsa Intro en la consola para terminar.
- La consola permanece visible durante esta fase para facilitar diagnósticos.
- Si el puerto 7860 está ocupado, cierra la otra instancia.
- Windows puede requerir WebView2 y mostrar avisos para EXE sin firma.

## Limitaciones expresas

Las modalidades que no necesitan IA local (extrusión de siluetas y relieve desde
mapa de alturas) son el objetivo de este primer empaquetado. **TripoSR y Depth
Anything V2 no están incluidos**. Requieren entornos Python y pesos externos
en rutas concretas, por lo que no se garantiza que funcionen dentro del ZIP.
Para esas dos modalidades, sigue usando la instalación Python del README.

Esto no es todavía un instalador MSI, una aplicación firmada ni un sistema
de actualizaciones automáticas. Tampoco incorpora todavía el editor de mallas
interactivo; es un empaquetado de las funciones existentes.
