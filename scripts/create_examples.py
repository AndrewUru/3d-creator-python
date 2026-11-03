from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

folder = Path(__file__).resolve().parents[1] / "examples"
folder.mkdir(exist_ok=True)
im = Image.new("RGBA", (480, 360), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((50, 50, 430, 310), radius=45, fill="#172d44")
im.save(folder / "silueta.png")
d.ellipse((160, 100, 320, 260), fill=(0, 0, 0, 0))
im.save(folder / "con-hueco.png")
im = Image.new("RGB", (480, 360), "white")
d = ImageDraw.Draw(im)
d.ellipse((30, 70, 210, 290), fill="black")
d.rectangle((280, 90, 440, 270), fill="black")
im.save(folder / "piezas-separadas.jpg")
Image.new("RGBA", (200, 200), (0, 0, 0, 0)).save(folder / "transparente.png")
im = Image.new("RGB", (640, 260), "white")
d = ImageDraw.Draw(im)
d.text((20, 15), "A O B", font=ImageFont.load_default(size=160), fill="black")
im.save(folder / "letras.png")
print(f"Ejemplos creados en {folder}")
