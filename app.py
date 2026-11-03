import os
import numpy as np

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from imagen3d.geometry import read_image, mask_image, build_mesh, export_mesh, report
from imagen3d.objects import generate_object
from imagen3d.relief import estimate_depth, prepare_heights, build_relief
from imagen3d.storage import new_folder, start_cleaner

def preview(path, mode, threshold, invert, min_area, smooth):
    try:
        image = read_image(path)
        mask = mask_image(image, mode, threshold, invert, min_area, smooth)
        return image, mask, "Máscara actualizada. Blanco = material; negro = vacío."
    except ValueError as exc:
        return None, None, f"**Revisa la imagen:** {exc}"


def generate(path, mode, threshold, invert, min_area, smooth, simplify, width, thickness, base, base_thickness):
    try:
        mask = mask_image(read_image(path), mode, threshold, invert, min_area, smooth)
        mesh, repaired = build_mesh(mask, width, thickness, simplify, base, base_thickness)
        stl, glb = export_mesh(mesh, new_folder())
        return mask, glb, stl, glb, report(mesh, repaired)
    except ValueError as exc:
        return None, None, None, None, f"**No se pudo generar:** {exc}"
    except Exception:
        return None, None, None, None, "**No se pudo resolver la geometría.** Prueba a simplificar o suavizar el contorno."


def generate_relief(path, mode, resolution, smooth, invert, gamma, width, height, base):
    try:
        image = read_image(path)
        folder = new_folder()
        depth = estimate_depth(image, folder) if mode == "Fotografía · IA local" else None
        heights = prepare_heights(image, depth, resolution, smooth, invert, gamma)
        mesh = build_relief(heights, width, height, base, image.height / image.width)
        stl, glb = export_mesh(mesh, folder)
        from PIL import Image
        preview = Image.fromarray(np.round(heights * 255).astype(np.uint8))
        map_path = folder / "mapa-alturas.png"
        preview.save(map_path)
        return preview, glb, stl, glb, str(map_path), report(mesh) + "\n\nRelieve local: blanco = mayor altura. La profundidad es relativa, no una medición real."
    except ValueError as exc:
        return None, None, None, None, None, str(exc)
    except Exception:
        return None, None, None, None, None, "No se pudo generar el relieve local. Reduce la resolución y revisa la imagen."


CSS = """
.gradio-container {max-width: 1320px !important; margin: auto;}
#hero {padding: 22px 4px 14px;}
#hero h1 {font-size: 2.5rem; letter-spacing: -.04em;}
#hero p {font-size: 1.05rem; max-width: 780px;}
.result-panel {border: 1px solid var(--border-color-primary); border-radius: 16px; padding: 14px;}
footer {display: none !important;}
"""


def create_app():
    with gr.Blocks(title="Imagen a 3D", delete_cache=(600, 86400)) as demo:
        gr.Markdown("# Imagen a 3D\nDe una idea plana a un objeto que puedes explorar. **Objetos completos, siluetas y relieves · Sin suscripciones ni tokens**", elem_id="hero")
        with gr.Tab("Objeto completo · sin placa"):
            gr.Markdown("Reconstruye un objeto con volumen por todos los lados usando IA local gratuita. Las zonas ocultas se estiman. Para manzanas, figuras y productos; para placas usa la pestaña Relieve.")
            with gr.Row():
                with gr.Column(scale=4):
                    object_source = gr.File(label="Foto de un único objeto · PNG/JPG", type="filepath", file_types=[".png", ".jpg", ".jpeg"])
                    object_size = gr.Number(value=100, minimum=1, maximum=1000, label="Dimensión mayor del objeto (mm)")
                    object_resolution = gr.Dropdown([96, 128, 192], value=128, label="Resolución 3D", info="96 para una prueba rápida, 128 normal, 192 más detalle y tiempo.")
                    object_run = gr.Button("Reconstruir objeto completo", variant="primary")
                    gr.Markdown("TripoSR en CPU, sin cuentas ni tokens. El fondo se elimina automáticamente; usa un PNG transparente si el recorte falla. Puede tardar varios minutos. La escala es la que indiques, no una medida extraída de la foto.")
                with gr.Column(scale=6):
                    object_cutout = gr.Image(label="Objeto separado del fondo", interactive=False, height=220)
                    object_viewer = gr.Model3D(label="Objeto completo · gira para ver la parte trasera", interactive=False, height=460)
                    object_status = gr.Markdown("Sube una foto para reconstruirla sin placa.")
                    object_stl = gr.File(label="STL · milímetros, sin colores", interactive=False)
                    object_glb = gr.File(label="GLB · metros, con colores", interactive=False)
            object_run.click(generate_object, [object_source, object_size, object_resolution],
                             [object_cutout, object_viewer, object_stl, object_glb, object_status],
                             concurrency_limit=1, concurrency_id="local_ai", trigger_mode="once")
        with gr.Tab("Dar volumen"):
            gr.Markdown("Da grosor a dibujos, letras y siluetas. Funciona con CPU y no envía tu imagen a ningún servicio. No reproduce los detalles interiores del dibujo.")
            with gr.Row():
                with gr.Column(scale=4, min_width=300):
                    source = gr.File(label="1 · Arrastra un PNG o JPG (máximo 15 MB)", file_types=[".png", ".jpg", ".jpeg"], type="filepath")
                    original = gr.Image(label="Imagen original", interactive=False, height=220)
                    with gr.Group():
                        gr.Markdown("### 2 · Separa la silueta")
                        mode = gr.Dropdown(["Automática", "Transparencia", "Luminancia"], value="Automática", label="Origen de la máscara")
                        threshold = gr.Slider(0, 255, value=127, step=1, label="Umbral de detección", info="Transparencia: conserva alfa mayor que el umbral. Luminancia: conserva los tonos más oscuros.")
                        invert = gr.Checkbox(label="Invertir máscara", value=False)
                        area = gr.Slider(1, 2000, value=20, step=1, label="Eliminar restos menores de (píxeles)")
                        smooth = gr.Slider(0, 5, value=0, step=1, label="Suavizado del borde")
                        simplify = gr.Slider(0, 5, value=0.8, step=0.1, label="Simplificación del contorno (píxeles)")
                        gr.Markdown("Se procesa a un máximo de 1600 px por lado. Valores altos pueden eliminar detalles finos.")
                    preview_button = gr.Button("Actualizar máscara")
                    with gr.Group():
                        gr.Markdown("### 3 · Define el tamaño")
                        width = gr.Number(value=100, minimum=1, maximum=1000, label="Anchura final (mm)")
                        thickness = gr.Number(value=5, minimum=0.2, maximum=200, label="Grosor del dibujo (mm)")
                        base = gr.Checkbox(label="Añadir base rectangular para unir las piezas")
                        base_thickness = gr.Number(value=2, minimum=0.2, maximum=50, label="Grosor de la base (mm)")
                        gr.Markdown("La base cubre el fondo de los huecos y mantiene la anchura indicada. El dibujo se solapa 0,1 mm con ella para formar un único sólido.")
                    generate_button = gr.Button("Generar volumen", variant="primary")
                with gr.Column(scale=6, min_width=320, elem_classes="result-panel"):
                    mask = gr.Image(label="Vista previa de la máscara", interactive=False, height=220, image_mode="L")
                    mask_status = gr.Markdown("Sube una imagen para ver la máscara.")
                    viewer = gr.Model3D(label="Tu modelo · arrastra para girar, usa la rueda para acercar", interactive=False, height=430)
                    result = gr.Markdown("El modelo aparecerá aquí después de generar.")
                    with gr.Row():
                        stl = gr.File(label="Descargar STL · milímetros", interactive=False)
                        glb = gr.File(label="Descargar GLB · metros", interactive=False)
                    gr.Markdown("STL no declara unidades: impórtalo como **milímetros**. El GLB está convertido a **metros** y conserva el tamaño físico.")
            mask_inputs = [source, mode, threshold, invert, area, smooth]
            preview_button.click(preview, mask_inputs, [original, mask, mask_status])
            for control in mask_inputs:
                control.change(preview, mask_inputs, [original, mask, mask_status], trigger_mode="always_last")
            generate_button.click(generate, mask_inputs + [simplify, width, thickness, base, base_thickness], [mask, viewer, stl, glb, result], trigger_mode="once", concurrency_limit=1)
        with gr.Tab("Relieve local gratuito"):
            gr.Markdown("Crea un bajorrelieve con detalles interiores y base rectangular cerrada. La IA estima profundidad; no reconstruye la parte trasera del objeto. Todo se procesa en tu ordenador.")
            with gr.Row():
                with gr.Column(scale=4):
                    photo = gr.File(label="Fotografía o mapa de alturas · PNG/JPG", type="filepath", file_types=[".png", ".jpg", ".jpeg"])
                    relief_mode = gr.Dropdown(["Fotografía · IA local", "Mapa de alturas · blanco elevado"], value="Fotografía · IA local", label="Interpretación de la imagen")
                    gr.Markdown("Para fotografías usa IA local. El modo mapa interpreta el brillo como altura y funciona sin modelos. La transparencia deja visible la base; para quitar el fondo usa un PNG recortado.")
                    resolution = gr.Slider(32, 384, value=192, step=16, label="Resolución de la malla (lado mayor)")
                    smoothing = gr.Slider(0, 5, value=1, step=0.5, label="Suavizado de profundidad")
                    reverse = gr.Checkbox(label="Invertir relieve")
                    gamma = gr.Slider(0.25, 4, value=1, step=0.05, label="Curva de alturas", info="Mayor que 1 reduce alturas intermedias; menor que 1 las eleva.")
                    rw = gr.Number(value=100, label="Anchura (mm)")
                    rh = gr.Number(value=5, label="Altura máxima del relieve sobre la base (mm)")
                    rb = gr.Number(value=2, label="Grosor de base (mm)")
                    run = gr.Button("Generar relieve local", variant="primary")
                    gr.Markdown("La primera instalación gratuita se hace con ` .venv/Scripts/python scripts/install_depth.py `. Después funciona sin conexión. La estimación en CPU puede tardar varios minutos.")
                with gr.Column(scale=6):
                    height_preview = gr.Image(label="Mapa de alturas · blanco elevado", interactive=False, image_mode="L", height=240)
                    relief_viewer = gr.Model3D(label="Relieve cerrado", interactive=False, height=430)
                    relief_status = gr.Markdown("Sube una imagen y genera el relieve. Ajusta los controles y vuelve a generar para corregirlo.")
                    with gr.Row():
                        relief_stl = gr.File(label="STL · milímetros", interactive=False)
                        relief_glb = gr.File(label="GLB · metros", interactive=False)
                        height_file = gr.File(label="Mapa de alturas PNG", interactive=False)
            run.click(generate_relief, [photo, relief_mode, resolution, smoothing, reverse, gamma, rw, rh, rb],
                      [height_preview, relief_viewer, relief_stl, relief_glb, height_file, relief_status],
                      concurrency_limit=1, concurrency_id="local_ai", trigger_mode="once")
        gr.Markdown("Archivos temporales disponibles durante 24 horas. Descarga los resultados que quieras conservar. Aplicación local, sin enlace público.")
    return demo


if __name__ == "__main__":
    print("Preparando Imagen a 3D…", flush=True)
    start_cleaner()
    demo = create_app().queue(max_size=16)
    # Preload Uvicorn's lazy protocol imports before Gradio's 5-second
    # thread-start deadline, which can expire on a busy Windows disk.
    import uvicorn
    uvicorn.Config(app=demo.app, log_level="warning").load()
    demo.launch(server_name="127.0.0.1", server_port=int(os.getenv("PORT", "7860")), share=False, inbrowser=False, max_file_size="15mb", theme=gr.themes.Soft(primary_hue="cyan", neutral_hue="slate"), css=CSS)
