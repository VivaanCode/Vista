"""Generate PNG theme icons (sun = light theme, moon = dark theme) with Pillow. Run: python scripts/generate_theme_icons.py"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Install Pillow: pip install Pillow")
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SIZE = 64
CX, CY = SIZE // 2, SIZE // 2


def draw_sun(path):
    """Sun icon: center circle + 8 rays (light theme = black)."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r_core = 6
    r_ray = 24
    w_ray = 3
    # center circle
    d.ellipse([CX - r_core, CY - r_core, CX + r_core, CY + r_core], fill=(0, 0, 0, 255))
    # 8 rays
    for i in range(8):
        a = i * (360 / 8)
        import math
        rad = math.radians(a)
        x1 = CX + (r_core + 2) * math.cos(rad)
        y1 = CY + (r_core + 2) * math.sin(rad)
        x2 = CX + r_ray * math.cos(rad)
        y2 = CY + r_ray * math.sin(rad)
        d.line([(x1, y1), (x2, y2)], fill=(0, 0, 0, 255), width=w_ray)
    img.save(path)
    print("Created", path)


def draw_moon_white(path):
    """Moon icon: crescent (dark theme = white)."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # outer circle (full moon)
    r_outer = 22
    d.ellipse([CX - r_outer, CY - r_outer, CX + r_outer, CY + r_outer], fill=(255, 255, 255, 255))
    # inner circle (cutout for crescent) offset left-up
    r_inner = 18
    ox, oy = 8, -6
    d.ellipse([CX - r_inner + ox, CY - r_inner + oy, CX + r_inner + ox, CY + r_inner + oy], fill=(0, 0, 0, 0))
    img.save(path)
    print("Created", path)


def main():
    ASSETS.mkdir(exist_ok=True)
    draw_sun(ASSETS / "sun.png")
    draw_moon_white(ASSETS / "moon.png")


if __name__ == "__main__":
    main()
