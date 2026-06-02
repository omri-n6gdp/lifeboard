#!/usr/bin/env python3
"""Draw the Lifeboard app icon (1024x1024 PNG): a warm dawn gradient squircle
with a 2x2 'board of cards' motif. No external assets needed."""
import pathlib

from PIL import Image, ImageDraw

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "app" / "icon_1024.png"
S = 1024


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    top, bot = (0xF7, 0xC8, 0x79), (0xCF, 0x62, 0x3A)
    bg = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(bg)
    for y in range(S):
        d.line([(0, y), (S, y)], fill=lerp(top, bot, y / (S - 1)))

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=230, fill=255)

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)

    dr = ImageDraw.Draw(img)
    cream, dark = (255, 250, 242, 255), (42, 37, 30, 255)
    cards = [(208, 208, cream), (546, 208, cream), (208, 546, cream), (546, 546, dark)]
    for x, y, col in cards:
        dr.rounded_rectangle([x, y, x + 270, y + 270], radius=46, fill=col)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
