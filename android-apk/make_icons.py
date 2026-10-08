"""Generate Android launcher icons from the project brand logo.

Produces, under app/src/main/res:
  * mipmap-<dpi>/ic_launcher.png + ic_launcher_round.png  (legacy launchers)
  * mipmap-<dpi>/ic_launcher_foreground.png               (adaptive icons)
  * mipmap-anydpi-v26/ic_launcher.xml, ic_launcher_round.xml
  * values/ic_launcher_background.xml                     (adaptive bg colour)

Run from anywhere:  python android-apk/make_icons.py
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', 'images', 'company-logo.png'))
RES = os.path.join(HERE, 'app', 'src', 'main', 'res')

# Legacy icon sizes (px) and adaptive foreground sizes (108dp canvas).
LEGACY = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
ADAPTIVE = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}

BACKGROUND_COLOR = '#FFFFFF'  # matches the logo's transparent field


def _logo(size):
    img = Image.open(SRC).convert('RGBA')
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return canvas


def _round(img):
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, img.width - 1, img.height - 1), fill=255)
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main():
    for dpi, px in LEGACY.items():
        folder = os.path.join(RES, f'mipmap-{dpi}')
        os.makedirs(folder, exist_ok=True)
        square = _logo(px)
        square.save(os.path.join(folder, 'ic_launcher.png'))
        _round(square).save(os.path.join(folder, 'ic_launcher_round.png'))

        # Adaptive foreground: keep the logo inside the ~66/108 safe zone.
        fg_size = ADAPTIVE[dpi]
        inner = int(fg_size * 0.66)
        fg = Image.new('RGBA', (fg_size, fg_size), (0, 0, 0, 0))
        logo = _logo(inner)
        off = (fg_size - inner) // 2
        fg.paste(logo, (off, off), logo)
        fg.save(os.path.join(folder, 'ic_launcher_foreground.png'))

    anydpi = os.path.join(RES, 'mipmap-anydpi-v26')
    os.makedirs(anydpi, exist_ok=True)
    for name in ('ic_launcher.xml', 'ic_launcher_round.xml'):
        with open(os.path.join(anydpi, name), 'w', encoding='utf-8') as fh:
            fh.write(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '    <background android:drawable="@color/ic_launcher_background" />\n'
                '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
                '</adaptive-icon>\n'
            )

    values = os.path.join(RES, 'values')
    os.makedirs(values, exist_ok=True)
    with open(os.path.join(values, 'ic_launcher_background.xml'), 'w', encoding='utf-8') as fh:
        fh.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<resources>\n'
            f'    <color name="ic_launcher_background">{BACKGROUND_COLOR}</color>\n'
            '</resources>\n'
        )

    print('Android launcher icons written (legacy + adaptive).')


if __name__ == '__main__':
    main()
