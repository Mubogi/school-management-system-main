"""Generate every platform icon from the company logo.

One source of truth for the JD Hub brand mark: the Windows ``.ico``, the
Android launcher (legacy + adaptive) and the web/PWA icons are all the company
logo on the brand-blue background, so the application shows the same icon
everywhere.

Run from anywhere:  python tools/generate_brand_icons.py
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOGO = os.path.join(ROOT, 'images', 'company-logo.png')

ANDROID_RES = os.path.join(ROOT, 'android-apk', 'app', 'src', 'main', 'res')
WEB_STATIC = os.path.join(ROOT, 'core', 'static', 'core')
WINDOWS_ICO = os.path.join(ROOT, 'images', 'icon.ico')

BRAND_BLUE = (30, 64, 175, 255)          # #1E40AF
BRAND_BLUE_HEX = '#1E40AF'

LEGACY = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
ADAPTIVE = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}


def _logo_mark(size, pad=0.12):
    """The company logo, cropped to its content and centred on a transparent
    canvas of ``size`` pixels with a proportional margin."""
    img = Image.open(LOGO).convert('RGBA')
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    inner = max(1, int(size * (1 - 2 * pad)))
    img.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return canvas


def _on_brand(size, pad=0.12, circle=False):
    """The logo on the brand-blue background (optionally circular)."""
    bg = Image.new('RGBA', (size, size), BRAND_BLUE)
    bg.alpha_composite(_logo_mark(size, pad))
    if circle:
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        out.paste(bg, (0, 0), mask)
        return out
    return bg


def _write_ico(path, base):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    base.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                           (64, 64), (128, 128), (256, 256)])


def android_icons():
    for dpi, px in LEGACY.items():
        folder = os.path.join(ANDROID_RES, f'mipmap-{dpi}')
        os.makedirs(folder, exist_ok=True)
        _on_brand(px).save(os.path.join(folder, 'ic_launcher.png'))
        _on_brand(px, circle=True).save(os.path.join(folder, 'ic_launcher_round.png'))

        # Adaptive foreground keeps the mark inside the ~66/108 safe zone; the
        # blue comes from the background layer so it is never double-drawn.
        fg = ADAPTIVE[dpi]
        fg_img = Image.new('RGBA', (fg, fg), (0, 0, 0, 0))
        logo = _logo_mark(int(fg * 0.62), pad=0.0)
        off = (fg - logo.width) // 2
        fg_img.alpha_composite(logo, (off, off))
        fg_img.save(os.path.join(folder, 'ic_launcher_foreground.png'))

    anydpi = os.path.join(ANDROID_RES, 'mipmap-anydpi-v26')
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

    values = os.path.join(ANDROID_RES, 'values')
    os.makedirs(values, exist_ok=True)
    with open(os.path.join(values, 'ic_launcher_background.xml'), 'w', encoding='utf-8') as fh:
        fh.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<resources>\n'
            f'    <color name="ic_launcher_background">{BRAND_BLUE_HEX}</color>\n'
            '</resources>\n'
        )


def web_icons():
    os.makedirs(WEB_STATIC, exist_ok=True)
    _on_brand(192).save(os.path.join(WEB_STATIC, 'icon-192.png'))
    _on_brand(512).save(os.path.join(WEB_STATIC, 'icon-512.png'))
    # Maskable icons need the mark inside the inner 80% safe circle.
    _on_brand(512, pad=0.22).save(os.path.join(WEB_STATIC, 'icon-maskable.png'))
    _write_ico(os.path.join(WEB_STATIC, 'favicon.ico'), _on_brand(256))


def windows_icon():
    _write_ico(WINDOWS_ICO, _on_brand(256))


def main():
    android_icons()
    web_icons()
    windows_icon()
    print('Brand icons written: Android launcher, web/PWA and Windows .ico.')


if __name__ == '__main__':
    main()
