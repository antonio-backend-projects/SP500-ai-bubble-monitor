"""Render the SP500 AI Bubble Monitor mark system (true alpha PNG + SVG).

Author: Antonio Trento — https://antoniotrento.net
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "images" / "logo"

TEAL = "#0E7C86"
TEAL_RGB = (14, 124, 134, 255)
INK = (19, 32, 39, 255)
TEAL_HI = (59, 181, 174, 255)
PAPER = (230, 237, 241, 255)
VB = 64.0


def spiral_points(
    n: int = 240,
    *,
    r0: float = 3.4,
    r1: float = 16.2,
    turns: float = 2.55,
) -> list[tuple[float, float]]:
    """Tight coil from the centre, opening from 12 o'clock."""
    cx = cy = 32.0
    t0 = 0.12 * math.pi
    t1 = t0 + turns * 2 * math.pi
    pts = []
    for i in range(n):
        u = i / (n - 1)
        t = t0 + (t1 - t0) * u
        r = r0 + (r1 - r0) * u
        x = cx + r * math.cos(t - math.pi / 2)
        y = cy + r * math.sin(t - math.pi / 2)
        pts.append((x, y))
    return pts


def svg_path(pts: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}" for i, (x, y) in enumerate(pts)
    )


def svg_doc(body: str, vb: str = "0 0 64 64") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
        f'fill="none" aria-hidden="true">\n{body}\n</svg>\n'
    )


def stamp_polyline(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[float, float]],
    *,
    fill: tuple[int, int, int, int],
    width: float,
) -> None:
    """Round-brush stroke — no PIL line-join hair."""
    r = max(width / 2.0, 0.6)
    step = max(r * 0.35, 0.4)
    prev = None
    for x, y in pts:
        if prev is not None:
            dx, dy = x - prev[0], y - prev[1]
            dist = math.hypot(dx, dy)
            n = max(int(dist / step), 1)
            for i in range(1, n + 1):
                t = i / n
                px = prev[0] + dx * t
                py = prev[1] + dy * t
                draw.ellipse((px - r, py - r, px + r, py + r), fill=fill)
        else:
            draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)
        prev = (x, y)


def stamp_circle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    *,
    fill: tuple[int, int, int, int],
    width: float,
    a0: float = 0.0,
    a1: float = 360.0,
) -> None:
    """Stroke an arc (degrees, 0 = 3 o'clock, CCW in math / clockwise PIL)."""
    sweep = (a1 - a0) % 360.0
    if sweep == 0:
        sweep = 360.0
    circ = 2 * math.pi * radius * (sweep / 360.0)
    n = max(int(circ / max(width * 0.25, 0.5)), 24)
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + sweep * i / n)
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    stamp_polyline(draw, pts, fill=fill, width=width)


def write_svgs() -> None:
    coil = svg_path(spiral_points())
    coil_inner = svg_path(spiral_points(r0=3.2, r1=15.6, turns=2.55))
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "mark-seal.svg").write_text(
        svg_doc(
            f'''  <defs>
    <mask id="coil-cut">
      <circle cx="32" cy="32" r="24" fill="#fff"/>
      <path d="{coil_inner}" stroke="#000" stroke-width="3.05"
            stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </mask>
  </defs>
  <circle cx="32" cy="32" r="24" fill="{TEAL}" mask="url(#coil-cut)"/>'''
        ),
        encoding="utf-8",
    )
    (OUT / "mark-coil.svg").write_text(
        svg_doc(
            f'  <path d="{coil}" stroke="{TEAL}" stroke-width="2.55" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        ),
        encoding="utf-8",
    )
    (OUT / "mark-coil-mono.svg").write_text(
        svg_doc(
            f'  <path d="{coil}" stroke="currentColor" stroke-width="2.55" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        ),
        encoding="utf-8",
    )
    (OUT / "mark-bubble.svg").write_text(
        svg_doc(
            f'''  <circle cx="32" cy="36.2" r="18.2" stroke="{TEAL}" stroke-width="2.5"/>
  <path d="M32 8 V15.2" stroke="{TEAL}" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="32" cy="8" r="2.05" fill="{TEAL}"/>'''
        ),
        encoding="utf-8",
    )
    (OUT / "mark-watch.svg").write_text(
        svg_doc(
            f'''  <circle cx="32" cy="32" r="20" stroke="{TEAL}" stroke-width="2.5"
          stroke-linecap="round" stroke-dasharray="109 16.7" stroke-dashoffset="-7"
          transform="rotate(-38 32 32)"/>
  <circle cx="32" cy="32" r="2.15" fill="{TEAL}"/>'''
        ),
        encoding="utf-8",
    )
    (OUT / "favicon.svg").write_text(
        (OUT / "mark-seal.svg").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    lockup = f'''  <svg x="0" y="0" width="64" height="64" viewBox="0 0 64 64">
    <defs>
      <mask id="coil-cut-l">
        <circle cx="32" cy="32" r="24" fill="#fff"/>
        <path d="{coil_inner}" stroke="#000" stroke-width="3.05"
              stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      </mask>
    </defs>
    <circle cx="32" cy="32" r="24" fill="{TEAL}" mask="url(#coil-cut-l)"/>
  </svg>
  <g font-family="Segoe UI, Helvetica Neue, Arial, sans-serif">
    <text x="76" y="30" font-size="20" font-weight="700" letter-spacing="0.06em" fill="#132027">SP500</text>
    <text x="76" y="48" font-size="8" font-weight="600" letter-spacing="0.28em" fill="{TEAL}">AI BUBBLE MONITOR</text>
  </g>'''
    (OUT / "lockup.svg").write_text(svg_doc(lockup, "0 0 280 64"), encoding="utf-8")

    lockup_i = lockup.replace("#132027", "#E6EDF1").replace(TEAL, "#3BB5AE")
    (OUT / "lockup-inverse.svg").write_text(
        svg_doc(lockup_i, "0 0 280 64"), encoding="utf-8"
    )


def render_mark(kind: str, size: int, color: tuple[int, int, int, int]) -> Image.Image:
    hi = 8
    S = size * hi
    k = S / VB
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 2.55 * k

    if kind == "seal":
        cx = cy = 32 * k
        R = 24 * k
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=color)
        cut = Image.new("L", (S, S), 0)
        cd = ImageDraw.Draw(cut)
        pts = [(x * k, y * k) for x, y in spiral_points(520, r0=3.2, r1=15.6, turns=2.55)]
        stamp_polyline(cd, pts, fill=255, width=3.05 * k)
        alpha = ImageChops.subtract(img.split()[3], cut)
        img.putalpha(alpha)
    elif kind == "coil":
        pts = [(x * k, y * k) for x, y in spiral_points(520, r0=3.4, r1=20.5, turns=2.7)]
        stamp_polyline(d, pts, fill=color, width=w)
    elif kind == "bubble":
        stamp_circle(d, 32 * k, 36.2 * k, 18.2 * k, fill=color, width=w)
        stamp_polyline(
            d, [(32 * k, 8 * k), (32 * k, 15.2 * k)], fill=color, width=w
        )
        pr = 2.05 * k
        d.ellipse(
            (32 * k - pr, 8 * k - pr, 32 * k + pr, 8 * k + pr),
            fill=color,
        )
    elif kind == "watch":
        # PIL/math 0° = east, clockwise. Gap at NE ≈ 310–350°.
        # 30° gap at NE (math degrees, 0 = east, CCW)
        stamp_circle(
            d, 32 * k, 32 * k, 20 * k, fill=color, width=w, a0=50, a1=50 + 330
        )
        hr = 2.15 * k
        d.ellipse(
            (32 * k - hr, 32 * k - hr, 32 * k + hr, 32 * k + hr),
            fill=color,
        )
    else:
        raise ValueError(kind)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def font(names: list[str], size: int) -> ImageFont.ImageFont:
    for name in names:
        p = Path(r"C:\Windows\Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def render_lockup(*, inverse: bool, height: int = 256) -> Image.Image:
    scale = height / 64
    hi = 3
    W, H = int(280 * scale), int(64 * scale)
    canvas = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    mark_px = int(64 * scale * hi)
    mark = render_mark("seal", mark_px, TEAL_HI if inverse else TEAL_RGB)
    canvas.alpha_composite(mark, (0, 0))
    overlay = ImageDraw.Draw(canvas)
    f_title = font(["segoeuib.ttf", "segoeui.ttf"], int(20 * scale * hi))
    f_sub = font(["seguisb.ttf", "segoeuisemibold.ttf", "segoeui.ttf"], int(8 * scale * hi))
    x = int(76 * scale * hi)
    overlay.text(
        (x, int(10 * scale * hi)),
        "SP500",
        font=f_title,
        fill=PAPER if inverse else INK,
    )
    overlay.text(
        (x, int(36 * scale * hi)),
        "AI BUBBLE MONITOR",
        font=f_sub,
        fill=TEAL_HI if inverse else TEAL_RGB,
    )
    return canvas.resize((W, H), Image.Resampling.LANCZOS)


def checkerboard(w: int, h: int, cell: int = 12) -> Image.Image:
    img = Image.new("RGBA", (w, h), (235, 237, 240, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(210, 214, 218, 255))
    return img


def preview_sheet(files: list[tuple[str, Image.Image]]) -> Image.Image:
    pad, cell = 28, 220
    cols = 3
    rows = math.ceil(len(files) / cols)
    w = pad * 2 + cols * cell + (cols - 1) * pad
    h = pad * 2 + rows * cell + (rows - 1) * pad + 36
    sheet = checkerboard(w, h, 14)
    d = ImageDraw.Draw(sheet)
    f = font(["segoeui.ttf"], 14)
    for i, (label, im) in enumerate(files):
        c, r = i % cols, i // cols
        x = pad + c * (cell + pad)
        y = pad + r * (cell + pad)
        thumb = im.copy()
        thumb.thumbnail((cell - 8, cell - 36), Image.Resampling.LANCZOS)
        tx = x + (cell - thumb.size[0]) // 2
        ty = y + (cell - 28 - thumb.size[1]) // 2
        sheet.alpha_composite(thumb, (tx, ty))
        d.text((x + 8, y + cell - 22), label, font=f, fill=(19, 32, 39, 255))
    return sheet


def corner_alpha(path: Path) -> int:
    im = Image.open(path)
    return im.getpixel((0, 0))[3] if im.mode == "RGBA" else -1


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in list(OUT.glob("logo-*.png")) + list(OUT.glob("mark-*-128.png")):
        stale.unlink()

    write_svgs()
    kinds = ("seal", "coil", "bubble", "watch")
    thumbs = []
    for kind in kinds:
        im = render_mark(kind, 512, TEAL_RGB)
        dest = OUT / f"mark-{kind}.png"
        im.save(dest, "PNG")
        render_mark(kind, 128, TEAL_RGB).save(OUT / f"mark-{kind}-128.png", "PNG")
        thumbs.append((kind, im))
        print(f"  {dest.name:24} corner_alpha={corner_alpha(dest)}")

    render_mark("seal", 32, TEAL_RGB).save(OUT / "favicon-32.png", "PNG")
    lock = render_lockup(inverse=False)
    lock_i = render_lockup(inverse=True)
    lock.save(OUT / "lockup.png", "PNG")
    lock_i.save(OUT / "lockup-inverse.png", "PNG")
    thumbs.append(("lockup", lock))
    preview_sheet(thumbs).save(OUT / "_preview-checkerboard.png", "PNG")
    print("preview: _preview-checkerboard.png (checkerboard = transparency)")


if __name__ == "__main__":
    main()
