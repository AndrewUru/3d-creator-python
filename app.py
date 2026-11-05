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


COLORS = {
    "body_background_fill": "#161514", "background_fill_primary": "#1f1d1b", "background_fill_secondary": "#1f1d1b",
    "block_background_fill": "#1f1d1b", "panel_background_fill": "#1f1d1b", "input_background_fill": "#2a2825",
    "input_background_fill_focus": "#2a2825", "border_color_primary": "#3a3733", "input_border_color": "#3a3733",
    "input_border_color_focus": "#f2792b", "block_border_color": "#3a3733", "body_text_color": "#edeae5",
    "body_text_color_subdued": "#a8a299", "block_label_text_color": "#a8a299", "block_title_text_color": "#c9c4bb",
    "block_label_background_fill": "transparent", "block_title_background_fill": "transparent",
    "block_info_text_color": "#a8a299", "checkbox_background_color": "#2a2825", "checkbox_border_color": "#5a554e",
    "checkbox_background_color_selected": "#f2792b", "checkbox_border_color_selected": "#f2792b",
    "slider_color": "#f2792b", "color_accent": "#f2792b", "color_accent_soft": "#3a2a1e", "link_text_color": "#f2792b",
    "button_primary_background_fill": "#f2792b", "button_primary_background_fill_hover": "#f78c45",
    "button_primary_text_color": "#1b1205", "button_secondary_background_fill": "#2a2825",
    "button_secondary_background_fill_hover": "#35322e", "button_secondary_text_color": "#edeae5",
}
THEME = gr.themes.Base(
    primary_hue="orange", neutral_hue="stone", radius_size=gr.themes.sizes.radius_sm,
    font=["Segoe UI Variable Text", "Segoe UI", "system-ui", "sans-serif"],
    font_mono=["Cascadia Mono", "Consolas", "monospace"],
).set(**COLORS, **{key + "_dark": value for key, value in COLORS.items() if key != "color_accent"})
FORCE_DARK = "() => document.body.classList.add('dark')"
VIEWPORT_COLOR = (0.125, 0.118, 0.11, 1)

CSS = """
.gradio-container {max-width: none !important; padding: 0 !important; margin: 0 !important;}
.gradio-container main, .gradio-container .main {max-width: none !important; padding: 0 16px !important; margin: 0 !important;}
footer {display: none !important;}
#brand {position: absolute; top: 12px; left: 0; z-index: 5; margin: 0; padding: 0; pointer-events: none;}
#brand p {margin: 0; font-size: 17px; font-weight: 650; letter-spacing: -.01em; color: #edeae5;}
#retention {position: absolute; top: 15px; right: 0; z-index: 5; margin: 0; padding: 0; width: auto; pointer-events: none;}
#retention p {margin: 0; font-size: 12.5px; color: #a8a299;}
#modes > div:first-child {padding-left: 124px; min-height: 48px;}
#modes button[role="tab"] {font-size: 14px; height: 48px;}
#modes button[role="tab"][aria-selected="true"] {color: #edeae5; font-weight: 600;}
#modes > .tabitem, #modes [role="tabpanel"] {padding: 12px 0 0; border: 0; background: none;}
.workspace {gap: 16px; flex-wrap: nowrap; align-items: stretch;}
.controls {flex: 0 0 340px !important; width: 340px; min-width: 0 !important; height: calc(100vh - 92px); overflow: hidden auto; gap: 12px;
           display: flex; flex-direction: column; flex-wrap: nowrap !important; padding-right: 4px; --neutral-200: #3a3733; scrollbar-width: thin; scrollbar-color: #3a3733 transparent;}
.controls > * {flex: none;}
.controls .lead p {margin: 0; font-size: 13px !important; line-height: 1.45; color: #c9c4bb !important;}
.controls .note p {margin: 0; font-size: 12.5px !important; line-height: 1.45; color: #a8a299 !important;}
.controls .section p {margin: 6px 0 0; font-size: 13px; font-weight: 600; color: #edeae5;}
.run {position: sticky; bottom: 0; z-index: 3; margin-top: auto; box-shadow: 0 -12px 12px #161514; min-height: 44px; flex-shrink: 0;}
.stage {flex: 1 1 0 !important; min-width: 0 !important; height: calc(100vh - 92px); gap: 12px; display: flex; flex-direction: column; flex-wrap: nowrap;}
.viewport {flex: 1 1 0; min-height: 240px; height: auto !important;}
.viewport > div, .viewport .model3D, .viewport canvas {height: 100% !important;}
.tray {flex: 0 0 168px; gap: 12px; flex-wrap: nowrap; align-items: stretch; min-height: 0;}
.tray .thumb {flex: 0 0 168px !important; min-width: 0 !important; height: 168px;}
.tray .readout {flex: 1 1 0 !important; min-width: 200px !important; height: 168px; overflow: hidden auto; flex-wrap: nowrap !important; gap: 0;
                padding: 10px 12px; border: 1px solid #3a3733; border-radius: 8px; background: #1f1d1b; scrollbar-width: thin; scrollbar-color: #3a3733 transparent;}
.tray .readout > * {flex: none; padding: 0; border: 0; background: none;}
.tray .readout p, .tray .readout li {margin: 0 0 6px; font-size: 13px !important; line-height: 1.5;}
.tray .files {flex: 0 0 260px !important; min-width: 0 !important; height: 168px; gap: 8px; flex-wrap: nowrap !important;}
.tray .files .block {flex: 1 1 0; min-height: 0; overflow: hidden; padding: 0 !important;}
.tray .files label[data-testid="block-label"] {position: absolute; top: 0; left: 0;}
.tray .files .block > :not(label):not([data-testid="status-tracker"]) {margin-top: 26px !important;}
.tray .files .empty {display: none;}
.tray .files .file-preview-holder, .tray .files .file-preview {margin: 0 !important; max-height: none; overflow: hidden;}
.tray .files table.file-preview, .tray .files tr.file {padding: 0 !important; margin: 0 !important;}
.tray .files td {padding: 2px 8px !important; margin: 0 !important; font-size: 12.5px;}
@media (max-width: 1080px) {
  #retention {display: none;}
  .tray {flex-basis: auto; flex-wrap: wrap;}
  .tray .files {flex: 1 1 100% !important; height: auto; flex-direction: row;}
  .tray .files .block {min-height: 56px;}
  .tray .thumb {flex: 1 1 0 !important;}
  .stage {height: auto;}
  .viewport {flex: 0 0 auto; height: 52vh !important;}
}
@media (max-width: 760px) {
  .workspace {flex-direction: column; flex-wrap: wrap;}
  .controls {flex: none !important; width: 100%; height: auto; overflow: visible;}
  .run {box-shadow: none; position: static;}
  .stage {width: 100%;}
  .tray .thumb, .tray .readout {flex: 1 1 100% !important;}
  #brand {position: static; padding: 12px 0 0;}
  #modes > div:first-child {padding-left: 0;}
}
"""


def create_app():
    with gr.Blocks(title="Imagen a 3D", delete_cache=(600, 86400)) as demo:
        gr.Markdown("Imagen a 3D", elem_id="brand")
        gr.Markdown("Local, sin enlace público · Descarga tus resultados: se borran a las 24 horas", elem_id="retention")
        with gr.Tabs(elem_id="modes"):
            with gr.Tab("Objeto completo"):
                with gr.Row(elem_classes="workspace"):
                    with gr.Column(elem_classes="controls"):
                        gr.Markdown("Reconstruye un objeto con volumen por todos los lados, sin placa. Las zonas ocultas se estiman. Para placas usa Relieve.", elem_classes="lead")
                        object_source = gr.File(label="Foto de un único objeto · PNG/JPG", type="filepath", file_types=[".png", ".jpg", ".jpeg"], height=156)
                        object_size = gr.Number(value=100, minimum=1, maximum=1000, label="Dimensión mayor del objeto (mm)")
                        object_resolution = gr.Dropdown([96, 128, 192], value=128, label="Resolución 3D", info="96 para una prueba rápida, 128 normal, 192 más detalle y tiempo.")
                        gr.Markdown("TripoSR en CPU: puede tardar varios minutos. El fondo se elimina automáticamente; usa un PNG transparente si el recorte falla. La escala es la que indiques, no una medida extraída de la foto.", elem_classes="note")
                        object_run = gr.Button("Reconstruir objeto completo", variant="primary", elem_classes="run")
                    with gr.Column(elem_classes="stage"):
                        object_viewer = gr.Model3D(label="Objeto completo · gira para ver la parte trasera", interactive=False, clear_color=VIEWPORT_COLOR, elem_classes="viewport")
                        with gr.Row(elem_classes="tray"):
                            object_cutout = gr.Image(label="Sin fondo", interactive=False, buttons=["fullscreen"], elem_classes="thumb")
                            with gr.Column(elem_classes="readout"):
                                object_status = gr.Markdown("Sube una foto para reconstruirla sin placa.")
                            with gr.Column(elem_classes="files"):
                                object_stl = gr.File(label="STL · milímetros, sin colores", interactive=False)
                                object_glb = gr.File(label="GLB · metros, con colores", interactive=False)
                object_run.click(generate_object, [object_source, object_size, object_resolution],
                                 [object_cutout, object_viewer, object_stl, object_glb, object_status],
                                 concurrency_limit=1, concurrency_id="local_ai", trigger_mode="once")
            with gr.Tab("Dar volumen"):
                with gr.Row(elem_classes="workspace"):
                    with gr.Column(elem_classes="controls"):
                        gr.Markdown("Da grosor a dibujos, letras y siluetas. No reproduce los detalles interiores del dibujo.", elem_classes="lead")
                        source = gr.File(label="PNG o JPG · máximo 15 MB", file_types=[".png", ".jpg", ".jpeg"], type="filepath", height=156)
                        gr.Markdown("Silueta", elem_classes="section")
                        mode = gr.Dropdown(["Automática", "Transparencia", "Luminancia"], value="Automática", label="Origen de la máscara")
                        threshold = gr.Slider(0, 255, value=127, step=1, label="Umbral de detección", info="Transparencia: conserva alfa mayor que el umbral. Luminancia: conserva los tonos más oscuros.")
                        invert = gr.Checkbox(label="Invertir máscara", value=False)
                        with gr.Accordion("Limpieza del contorno", open=False):
                            area = gr.Slider(1, 2000, value=20, step=1, label="Eliminar restos menores de (píxeles)")
                            smooth = gr.Slider(0, 5, value=0, step=1, label="Suavizado del borde")
                            simplify = gr.Slider(0, 5, value=0.8, step=0.1, label="Simplificación del contorno (píxeles)")
                            gr.Markdown("Se procesa a un máximo de 1600 px por lado. Valores altos pueden eliminar detalles finos.", elem_classes="note")
                        preview_button = gr.Button("Actualizar máscara")
                        gr.Markdown("Tamaño", elem_classes="section")
                        width = gr.Number(value=100, minimum=1, maximum=1000, label="Anchura final (mm)")
                        thickness = gr.Number(value=5, minimum=0.2, maximum=200, label="Grosor del dibujo (mm)")
                        base = gr.Checkbox(label="Añadir base rectangular para unir las piezas")
                        base_thickness = gr.Number(value=2, minimum=0.2, maximum=50, label="Grosor de la base (mm)")
                        gr.Markdown("La base cubre el fondo de los huecos y mantiene la anchura indicada. El dibujo se solapa 0,1 mm con ella para formar un único sólido.", elem_classes="note")
                        generate_button = gr.Button("Generar volumen", variant="primary", elem_classes="run")
                    with gr.Column(elem_classes="stage"):
                        viewer = gr.Model3D(label="Tu modelo · arrastra para girar, usa la rueda para acercar", interactive=False, clear_color=VIEWPORT_COLOR, elem_classes="viewport")
                        with gr.Row(elem_classes="tray"):
                            original = gr.Image(label="Original", interactive=False, buttons=["fullscreen"], elem_classes="thumb")
                            mask = gr.Image(label="Máscara", interactive=False, buttons=["fullscreen"], image_mode="L", elem_classes="thumb")
                            with gr.Column(elem_classes="readout"):
                                mask_status = gr.Markdown("Sube una imagen para ver la máscara.")
                                result = gr.Markdown("El modelo aparecerá aquí después de generar.")
                                gr.Markdown("STL no declara unidades: impórtalo como **milímetros**. El GLB está convertido a **metros** y conserva el tamaño físico.")
                            with gr.Column(elem_classes="files"):
                                stl = gr.File(label="Descargar STL · milímetros", interactive=False)
                                glb = gr.File(label="Descargar GLB · metros", interactive=False)
                mask_inputs = [source, mode, threshold, invert, area, smooth]
                preview_button.click(preview, mask_inputs, [original, mask, mask_status])
                for control in mask_inputs:
                    control.change(preview, mask_inputs, [original, mask, mask_status], trigger_mode="always_last")
                generate_button.click(generate, mask_inputs + [simplify, width, thickness, base, base_thickness], [mask, viewer, stl, glb, result], trigger_mode="once", concurrency_limit=1)
            with gr.Tab("Relieve"):
                with gr.Row(elem_classes="workspace"):
                    with gr.Column(elem_classes="controls"):
                        gr.Markdown("Crea un bajorrelieve con detalles interiores y base rectangular cerrada. La IA estima profundidad; no reconstruye la parte trasera.", elem_classes="lead")
                        photo = gr.File(label="Fotografía o mapa de alturas · PNG/JPG", type="filepath", file_types=[".png", ".jpg", ".jpeg"], height=156)
                        relief_mode = gr.Dropdown(["Fotografía · IA local", "Mapa de alturas · blanco elevado"], value="Fotografía · IA local", label="Interpretación de la imagen")
                        gr.Markdown("El modo mapa interpreta el brillo como altura y funciona sin modelos. La transparencia deja visible la base; para quitar el fondo usa un PNG recortado.", elem_classes="note")
                        rw = gr.Number(value=100, label="Anchura (mm)")
                        rh = gr.Number(value=5, label="Altura máxima del relieve sobre la base (mm)")
                        rb = gr.Number(value=2, label="Grosor de base (mm)")
                        with gr.Accordion("Ajustes de malla", open=False):
                            resolution = gr.Slider(32, 384, value=192, step=16, label="Resolución de la malla (lado mayor)")
                            smoothing = gr.Slider(0, 5, value=1, step=0.5, label="Suavizado de profundidad")
                            reverse = gr.Checkbox(label="Invertir relieve")
                            gamma = gr.Slider(0.25, 4, value=1, step=0.05, label="Curva de alturas", info="Mayor que 1 reduce alturas intermedias; menor que 1 las eleva.")
                        gr.Markdown("La primera instalación gratuita se hace con ` .venv/Scripts/python scripts/install_depth.py `. Después funciona sin conexión. La estimación en CPU puede tardar varios minutos.", elem_classes="note")
                        run = gr.Button("Generar relieve local", variant="primary", elem_classes="run")
                    with gr.Column(elem_classes="stage"):
                        relief_viewer = gr.Model3D(label="Relieve cerrado", interactive=False, clear_color=VIEWPORT_COLOR, elem_classes="viewport")
                        with gr.Row(elem_classes="tray"):
                            height_preview = gr.Image(label="Mapa de alturas", interactive=False, buttons=["fullscreen"], image_mode="L", elem_classes="thumb")
                            with gr.Column(elem_classes="readout"):
                                relief_status = gr.Markdown("Sube una imagen y genera el relieve. Ajusta los controles y vuelve a generar para corregirlo.")
                            with gr.Column(elem_classes="files"):
                                relief_stl = gr.File(label="STL · milímetros", interactive=False)
                                relief_glb = gr.File(label="GLB · metros", interactive=False)
                                height_file = gr.File(label="Mapa de alturas PNG", interactive=False)
                run.click(generate_relief, [photo, relief_mode, resolution, smoothing, reverse, gamma, rw, rh, rb],
                          [height_preview, relief_viewer, relief_stl, relief_glb, height_file, relief_status],
                          concurrency_limit=1, concurrency_id="local_ai", trigger_mode="once")
    return demo


def start_server(port, block=True):
    """Arranca el servidor local. Con block=False devuelve (demo, url) sin bloquear."""
    print("Preparando Imagen a 3D…", flush=True)
    start_cleaner()
    demo = create_app().queue(max_size=16)
    # Preload Uvicorn's lazy protocol imports before Gradio's 5-second
    # thread-start deadline, which can expire on a busy Windows disk.
    import uvicorn
    uvicorn.Config(app=demo.app, log_level="warning").load()
    _, url, _ = demo.launch(server_name="127.0.0.1", server_port=port, share=False, inbrowser=False, max_file_size="15mb", theme=THEME, css=CSS, js=FORCE_DARK, prevent_thread_lock=not block)
    return demo, url


if __name__ == "__main__":
    start_server(int(os.getenv("PORT", "7860")))
