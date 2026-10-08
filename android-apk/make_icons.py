"""Generate Android launcher icons from the project logo."""
import os
from PIL import Image

SRC = os.path.join(os.path.dirname(__file__), '..', 'images', 'company-logo.png')
RES = os.path.join(os.path.dirname(__file__), 'app', 'src', 'main', 'res')

SIZES = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}

src = Image.open(SRC).convert('RGBA')
for dpi, px in SIZES.items():
    folder = os.path.join(RES, f'mipmap-{dpi}')
    os.makedirs(folder, exist_ok=True)
    icon = src.resize((px, px), Image.LANCZOS)
    icon.save(os.path.join(folder, 'ic_launcher.png'))
    icon.save(os.path.join(folder, 'ic_launcher_round.png'))
print('Android launcher icons written.')
