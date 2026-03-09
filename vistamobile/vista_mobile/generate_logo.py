#!/usr/bin/env python3
"""Generate Vista app logo and icons."""
from PIL import Image, ImageDraw, ImageFont
import os
import math

BASE = os.path.dirname(os.path.abspath(__file__))

# Brand colors
TEAL = (88, 178, 192)       # #58B2C0
DARK_TEAL = (60, 140, 155)  # darker variant
WHITE = (255, 255, 255)
LIGHT_BG = (245, 243, 240)  # #F5F3F0

def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*radius, y0 + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*radius, y0, x1, y0 + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*radius, x0 + 2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*radius, y1 - 2*radius, x1, y1], 0, 90, fill=fill)

def draw_vista_icon(size, padding_ratio=0.12, bg_color=None, round_corners=True):
    """Draw the Vista 'V' feather icon at given size."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    pad = int(size * padding_ratio)
    
    if bg_color:
        if round_corners:
            corner = int(size * 0.22)
            draw_rounded_rect(draw, [0, 0, size-1, size-1], corner, bg_color)
        else:
            draw.rectangle([0, 0, size-1, size-1], fill=bg_color)
    
    # Draw a stylized feather/V shape
    cx = size // 2
    cy = size // 2
    
    # The "V" is made of elegant curved strokes suggesting a feather quill
    # Main V shape
    top_y = pad + int(size * 0.08)
    bottom_y = size - pad - int(size * 0.05)
    mid_y = bottom_y
    left_x = pad + int(size * 0.05)
    right_x = size - pad - int(size * 0.05)
    
    # Stroke width proportional to size
    stroke = max(2, int(size * 0.045))
    
    # Draw feather-like V with multiple barbs
    # Left stroke of V
    points_left = []
    points_right = []
    
    num_steps = 40
    for i in range(num_steps + 1):
        t = i / num_steps
        # Left arm: from top-left curving down to bottom-center
        x = left_x + (cx - left_x) * t + math.sin(t * math.pi) * size * 0.04
        y = top_y + (mid_y - top_y) * (t ** 0.85)
        points_left.append((x, y))
    
    for i in range(num_steps + 1):
        t = i / num_steps
        # Right arm: from top-right curving down to bottom-center
        x = right_x + (cx - right_x) * t - math.sin(t * math.pi) * size * 0.04
        y = top_y + (mid_y - top_y) * (t ** 0.85)
        points_right.append((x, y))
    
    # Draw the V strokes
    icon_color = WHITE if bg_color else TEAL
    
    # Draw left arm with thickness
    for i in range(len(points_left) - 1):
        x1, y1 = points_left[i]
        x2, y2 = points_left[i + 1]
        # Taper the stroke
        progress = i / len(points_left)
        w = stroke * (1.5 - progress * 0.8)
        draw.line([(x1, y1), (x2, y2)], fill=icon_color, width=max(1, int(w)))
    
    # Draw right arm with thickness  
    for i in range(len(points_right) - 1):
        x1, y1 = points_right[i]
        x2, y2 = points_right[i + 1]
        progress = i / len(points_right)
        w = stroke * (1.5 - progress * 0.8)
        draw.line([(x1, y1), (x2, y2)], fill=icon_color, width=max(1, int(w)))
    
    # Draw feather barbs (small lines branching off the V arms)
    barb_color_l = (*icon_color[:3], 160) if len(icon_color) == 3 else (*icon_color[:3], 160)
    
    # Left barbs
    for i in range(5, len(points_left) - 8, 4):
        x, y = points_left[i]
        t = i / len(points_left)
        barb_len = size * 0.08 * (1 - t * 0.6)
        angle = -0.6 - t * 0.3
        ex = x + barb_len * math.cos(angle)
        ey = y + barb_len * math.sin(angle)
        bw = max(1, int(stroke * 0.5))
        draw.line([(x, y), (ex, ey)], fill=icon_color, width=bw)
    
    # Right barbs
    for i in range(5, len(points_right) - 8, 4):
        x, y = points_right[i]
        t = i / len(points_right)
        barb_len = size * 0.08 * (1 - t * 0.6)
        angle = math.pi + 0.6 + t * 0.3
        ex = x + barb_len * math.cos(angle)
        ey = y + barb_len * math.sin(angle)
        bw = max(1, int(stroke * 0.5))
        draw.line([(x, y), (ex, ey)], fill=icon_color, width=bw)
    
    # Draw center quill line (thin line down the V center)
    quill_top = top_y + int(size * 0.35)
    quill_bottom = bottom_y + int(size * 0.02)
    draw.line([(cx, quill_top), (cx, quill_bottom)], fill=icon_color, width=max(1, stroke // 2))
    
    # Small circle at the bottom tip
    tip_r = max(2, int(size * 0.02))
    draw.ellipse([cx - tip_r, bottom_y - tip_r, cx + tip_r, bottom_y + tip_r], fill=icon_color)
    
    return img


def generate_all():
    # 1. Main logo.png for use in-app (512x512, transparent bg with teal icon)
    logo = draw_vista_icon(512, bg_color=None)
    logo_path = os.path.join(BASE, 'assets', 'logo.png')
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)
    logo.save(logo_path, 'PNG')
    print(f"Created {logo_path}")
    
    # 2. App icon (teal background, white V feather) - for Android & iOS
    icon_1024 = draw_vista_icon(1024, padding_ratio=0.18, bg_color=TEAL, round_corners=False)
    
    # Android mipmap sizes
    android_sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192,
    }
    
    android_res = os.path.join(BASE, 'android', 'app', 'src', 'main', 'res')
    for folder, sz in android_sizes.items():
        resized = icon_1024.resize((sz, sz), Image.LANCZOS)
        out = os.path.join(android_res, folder, 'ic_launcher.png')
        resized.save(out, 'PNG')
        print(f"Created {out}")
    
    # Foreground for adaptive icon (just the V on transparent)
    fg_1024 = draw_vista_icon(1024, padding_ratio=0.26, bg_color=None, round_corners=False)
    for folder, sz in android_sizes.items():
        resized = fg_1024.resize((sz, sz), Image.LANCZOS)
        # Save white version for adaptive icon foreground
        out = os.path.join(android_res, folder, 'ic_launcher_foreground.png')
        # Need white icon on transparent for foreground
        fg_white = draw_vista_icon(sz, padding_ratio=0.26, bg_color=None, round_corners=False)
        fg_white.save(out, 'PNG')
        print(f"Created {out}")
    
    # iOS icon sizes
    ios_icons = {
        'Icon-App-1024x1024@1x.png': 1024,
        'Icon-App-20x20@1x.png': 20,
        'Icon-App-20x20@2x.png': 40,
        'Icon-App-20x20@3x.png': 60,
        'Icon-App-29x29@1x.png': 29,
        'Icon-App-29x29@2x.png': 58,
        'Icon-App-29x29@3x.png': 87,
        'Icon-App-40x40@1x.png': 40,
        'Icon-App-40x40@2x.png': 80,
        'Icon-App-40x40@3x.png': 120,
        'Icon-App-60x60@2x.png': 120,
        'Icon-App-60x60@3x.png': 180,
        'Icon-App-76x76@1x.png': 76,
        'Icon-App-76x76@2x.png': 152,
        'Icon-App-83.5x83.5@2x.png': 167,
    }
    
    ios_dir = os.path.join(BASE, 'ios', 'Runner', 'Assets.xcassets', 'AppIcon.appiconset')
    # iOS icons need NO transparency, solid background, no rounded corners (iOS adds them)
    icon_1024_solid = draw_vista_icon(1024, padding_ratio=0.18, bg_color=TEAL, round_corners=False)
    # Fill alpha with solid
    bg = Image.new('RGBA', (1024, 1024), TEAL + (255,))
    icon_no_alpha = Image.alpha_composite(bg, icon_1024_solid)
    icon_rgb = icon_no_alpha.convert('RGB')
    
    for fname, sz in ios_icons.items():
        resized = icon_rgb.resize((sz, sz), Image.LANCZOS)
        out = os.path.join(ios_dir, fname)
        resized.save(out, 'PNG')
        print(f"Created {out}")
    
    # Web favicon
    web_dir = os.path.join(BASE, 'web')
    favicon = icon_1024.resize((192, 192), Image.LANCZOS)
    favicon.save(os.path.join(web_dir, 'icons', 'Icon-192.png'), 'PNG')
    print(f"Created Icon-192.png")
    favicon_512 = icon_1024.resize((512, 512), Image.LANCZOS)
    favicon_512.save(os.path.join(web_dir, 'icons', 'Icon-512.png'), 'PNG')
    print(f"Created Icon-512.png")
    favicon_16 = icon_1024.resize((16, 16), Image.LANCZOS)
    favicon_16.save(os.path.join(web_dir, 'favicon.png'), 'PNG')
    print(f"Created favicon.png")
    
    print("\nDone! All icons generated.")


if __name__ == '__main__':
    generate_all()
