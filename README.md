# Imagen a 3D

Aplicación Python local con Gradio: convierte siluetas y fotografías en sólidos mediante CPU. La interfaz no usa Meshy, claves API, suscripciones ni tokens. El modo de fotografías utiliza un modelo gratuito descargado una vez; después funciona sin conexión.

## Inicio en Windows (PowerShell)

Requiere Python 3.12 de 64 bits. Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python app.py
```

Abre http://127.0.0.1:7860. No es necesario activar el entorno ni cambiar la política de ejecución. Si el entorno ya está instalado, basta con el último comando. Detén el servidor con Ctrl+C.

## Ventana de escritorio

Para usar la aplicación en su propia ventana, sin abrir el navegador:

```powershell
.\.venv\Scripts\python desktop.py
```

Usa un puerto libre automáticamente y, al cerrar la ventana, detiene el servidor. En Windows necesita el runtime WebView2, incluido en Windows 11. En Linux, `pywebview` requiere además GTK o Qt.

## Inicio en Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python app.py
```

En Debian/Ubuntu puede ser necesario instalar el paquete del sistema `python3.12-venv`. OpenCV usa la variante headless: no exige escritorio ni bibliotecas Qt. Instalación y ejecución verificadas en Windows; Linux no se ha ejecutado en este entorno. `requirements-lock.txt` registra todas las versiones del entorno de verificación; `requirements.txt` fija las dependencias directas para ambos sistemas.

## Dar volumen

1. Sube un PNG o JPG. En `examples/` hay siluetas, un anillo, letras A/O/B, piezas separadas y un archivo transparente para probar errores.
2. Revisa la máscara: blanco es material y negro es vacío. Automática usa el canal alfa si existe transparencia; en otro caso utiliza tonos oscuros. Invierte para figuras claras sobre fondo oscuro. El umbral también afecta al canal alfa.
3. Ajusta limpieza, suavizado, simplificación, anchura y grosor. La anchura se mide sobre el contorno útil, no sobre el lienzo completo.
4. Genera y gira o amplía el modelo. Descarga STL o GLB.

Se conservan huecos interiores e islas anidadas. Los contornos inválidos se reparan mediante Shapely cuando es posible, y se rechazan los que no tienen área. La triangulación utiliza Earcut. La base realiza una unión booleana real mediante Manifold, cubre los huecos por debajo y une componentes separados. Mantiene la anchura indicada; el relieve se solapa 0,1 mm con la base (o la mitad del relieve para grosores muy pequeños). Altura total = base + relieve − solape.

**Unidades:** la geometría interna y el STL usan milímetros. STL no incluye una unidad explícita: configura el laminador/importador en mm. GLB usa metros, por lo que sus coordenadas se dividen por 1000. Ambos conservan el mismo tamaño físico.

No reconstruye detalles internos, colores o profundidad de una fotografía. Una malla estanca no garantiza una impresión viable: revisa detalles finos, orientación, soportes y ajustes del laminador.

## Objeto completo sin placa

Para frutas, figuras y productos con volumen por todos los lados, utiliza la primera pestaña **Objeto completo · sin placa**. El modo Relieve produce una placa con alturas y no sirve como sustituto de la reconstrucción completa.

Instalación gratuita, una sola vez:

```powershell
.\.venv\Scripts\python scripts/install_local_ai.py
```

El instalador prepara `.venv-tripo`, TripoSR y su modelo (aproximadamente 1,7 GB), además de un modelo de recorte del fondo. No modifica `.venv-ai`, usado por los relieves. Las generaciones se ejecutan localmente en CPU con Hugging Face en modo offline, sin cuentas ni tokens.

Sube un único objeto, indica su dimensión mayor en milímetros y pulsa **Reconstruir objeto completo**. La resolución 96 sirve para pruebas rápidas, 128 es la normal y 192 requiere más tiempo y memoria. El fondo se elimina automáticamente; también puedes aportar un PNG transparente. La previsualización del recorte permite detectar si se ha perdido parte del objeto. GLB conserva colores por vértice, STL solo geometría.

La parte trasera es estimada: una sola imagen no determina su geometría real. No se garantiza que todas las generaciones sean estancas o imprimibles; el resultado informa del cierre y del número de piezas. Hay un límite de 30 minutos por generación. Los errores del proceso se conservan en `proceso.log`, dentro de la carpeta temporal indicada por la interfaz.

## Relieve local gratuito

1. Instala una vez el modelo de profundidad (requiere Internet para descargar dependencias y unos 100 MB de pesos; PyTorch puede ocupar bastante más):

```powershell
.\.venv\Scripts\python scripts/install_depth.py
```

2. Inicia la aplicación y abre **Relieve local gratuito**.
3. Sube una fotografía y selecciona **Fotografía · IA local**.
4. Ajusta anchura, altura del relieve, base, suavizado, inversión y curva de alturas.
5. Genera, revisa el mapa de alturas y gira la malla. Descarga STL, GLB y el mapa PNG.

El modelo es [Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), licencia Apache 2.0. Se ejecuta en CPU dentro de `.venv-ai`, separado del entorno de la interfaz. La inferencia carga únicamente archivos locales y tiene el acceso a Hugging Face en modo offline. No necesita cuenta. Puede tardar varios minutos; se limita a una generación simultánea y diez minutos por estimación.

**Mapa de alturas · blanco elevado** funciona sin instalar IA: interpreta blanco como altura máxima y negro como base. Es apropiado para mapas preparados, no para deducir profundidad de las sombras de una fotografía. El PNG exportado se puede editar y volver a subir en este modo; pon suavizado a 0 y curva a 1 para conservar sus alturas cuantizadas.

La malla conserva la proporción de la imagen, utiliza hasta 384 puntos por lado y tiene paredes y fondo cerrados. La transparencia baja el relieve hasta la base; no se elimina automáticamente el fondo de fotografías opacas. Recorta el fondo en un PNG transparente si lo necesitas. La altura total máxima es base + relieve, aunque un mapa sin blancos puede producir menos altura.

La profundidad es relativa y estimada, no una medición. Este modo genera bajorrelieves con base rectangular, no objetos completos ni sus caras ocultas. El código anterior de Meshy queda aislado en `providers.py` y no se importa desde la aplicación. El modo Objeto completo usa TripoSR en un entorno separado `.venv-tripo`.

## Privacidad y límites

- Escucha exclusivamente en `127.0.0.1`, sin enlace público ni analítica de Gradio. No despliegues esta versión tal cual en Internet: está diseñada para uso personal local.
- PNG/JPEG por contenido, hasta 15 MB, 16 millones de píxeles, 8192 px por lado y mínimo 8 px. EXIF se aplica al orientar la imagen; las entradas del modelo se guardan sin esos metadatos.
- La máscara se procesa hasta 1600 px por lado y admite hasta 50 000 vértices de contorno; el remuestreo puede perder detalles.
- Cada resultado usa una carpeta aleatoria independiente. No se aceptan rutas de salida proporcionadas por el usuario. La caché de Gradio y los resultados temporales se limpian tras 24 horas, con revisiones cada 10 minutos mientras se ejecuta la aplicación. Al reiniciar también se limpian resultados caducados. Las imágenes no se envían a servicios externos.
- No se necesitan credenciales. Los archivos temporales siguen sujetos a los permisos de tu usuario del sistema operativo.

## Pruebas

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts/create_examples.py
```

En Linux sustituye `.\.venv\Scripts\python` por `.venv/bin/python`. Las pruebas de API usan **respuestas simuladas solo en los tests** mediante `httpx.MockTransport`: no prueban la calidad de una generación real ni consumen créditos. Las pruebas geométricas recargan STL y GLB y verifican proporciones, unidades, huecos, conectividad y volumen.

## Verificación

Las pruebas geométricas incluyen volumen analítico de una rampa, cierre de superficies planas y estrechas, inversión, transparencia, profundidad relativa y equivalencia física entre STL y GLB. `scripts/smoke_server.py` comprueba la extrusión y el relieve por HTTP con un servidor ya iniciado.

## Organización

- `app.py`: interfaz en español y eventos.
- `imagen3d/geometry.py`: lectura, máscara, contornos, mallas y exportación.
- `imagen3d/relief.py`: profundidad local, alturas y mallas de relieve.
- `scripts/install_depth.py`, `scripts/depth_worker.py`: instalación gratuita e inferencia offline.
- `imagen3d/providers.py`: integración antigua de Meshy, fuera del flujo de la aplicación.
- `imagen3d/storage.py`: resultados aislados y limpieza temporal.
- `tests/`: comprobaciones geométricas y pruebas simuladas de API.
- `scripts/create_examples.py`, `examples/`: imágenes sintéticas reproducibles.
