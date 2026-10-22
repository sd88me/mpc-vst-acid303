#!/usr/bin/env python3
"""Draws Model-303's MPC skin for the MPC's 1280x628 plugin area: a silver panel in the manner of the modded 303 clones
(the TD-3-MO's knobs, bat toggles, red buttons and lettering as the reference), drawn from scratch -- no photo, no maker's
name or mark -- in Barlow Semi Condensed (SIL OFL, skin/assets/).

    python3 skin/make_skin.py vst/          # -> vst/art/*.png, vst/layout.conf, vst/preview/*.png

Each tab is drawn once at 2x (plate, lettering, scales, section boxes); each control is then a filmstrip or a set of
pictures cut from that tab with the control in each position, so a frame sits exactly over its place in the background
(the method of Model-72's skin). Needs Pillow."""
import json
import math
import os
import shutil
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
SS = 2
W, H = 1280, 628
Y_OFF = 86                 # layout y = plugin y + 86
INK = (34, 34, 36)
DIM = (92, 92, 96)
RED = (222, 38, 34)
FRAMES = 64
SWEEP = 300                # a pot's travel in degrees (-150 .. +150)

FONTS = {}


def font(size, weight="SemiBold"):
    k = (size, weight)
    if k not in FONTS:
        FONTS[k] = ImageFont.truetype(os.path.join(A, "BarlowSemiCondensed-%s.ttf" % weight), int(round(size * SS)))
    return FONTS[k]


def even(x):
    n = int(math.ceil(x))
    return n + (n & 1)


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


# ---------------------------------------------------------------- the plate

# The module: a silver slab on the dark page, lit from the top left. Its face (screen px) and thickness:
FACE = (12, 10, 1268, 604)
DEPTH = 9
RADIUS = 22


def diag(w, h, lo, hi):
    """A top-left (hi) to bottom-right (lo) gradient, L."""
    gy = Image.linear_gradient("L").resize((w, h))                      # 0 top .. 255 bottom
    gx = Image.linear_gradient("L").transpose(Image.Transpose.TRANSPOSE).resize((w, h))   # 0 left .. 255 right
    g = ImageChops.add(gx, gy, 2.0)                                      # (x + y) / 2
    return g.point(lambda v: int(hi + (lo - hi) * v / 255))


def rounded_mask(size, box, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=r, fill=255)
    return m


def plate(w, h):
    """The page: dark ground, the slab's shadow and edge, its brushed silver face with a bevel round it, four screws."""
    page = Image.new("RGBA", (w, h))
    pg = Image.linear_gradient("L").resize((w, h)).point(lambda v: 22 - v * 12 // 255)
    page.paste(Image.merge("RGB", (pg, pg, pg.point(lambda v: v + 2))).convert("RGBA"))
    x0, y0, x1, y1 = [v * SS for v in FACE]
    R, D = RADIUS * SS, DEPTH * SS
    # drop shadow under the slab, then its side (the face's depth, darker toward the bottom)
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 6 * SS, y0 + 12 * SS, x1 + 6 * SS, y1 + D + 10 * SS), radius=R, fill=(0, 0, 0, 200))
    page.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * SS)))
    side = Image.linear_gradient("L").resize((w, h)).point(lambda v: 150 - v * 90 // 255)
    side_rgb = Image.merge("RGB", (side, side, side.point(lambda v: min(255, v + 4)))).convert("RGBA")
    page.paste(side_rgb, (0, 0), rounded_mask((w, h), (x0, y0 + D, x1, y1 + D), R))
    # the face: brushed grain, light from the top left, a soft vignette
    fw, fh = x1 - x0, y1 - y0
    base = diag(fw, fh, 188, 226)
    grain = Image.effect_noise((fw // 10, fh), 12).resize((fw, fh), Image.BILINEAR)
    face = ImageChops.add(base, grain, 1.0, -128)
    vig = Image.radial_gradient("L").resize((fw, fh)).point(lambda v: max(0, v - 150) * 30 // 105)
    face = ImageChops.subtract(face, vig)
    face_rgb = Image.merge("RGB", (face, face.point(lambda v: min(255, v + 1)), face.point(lambda v: min(255, v + 4)))).convert("RGBA")
    fm = rounded_mask((fw, fh), (0, 0, fw - 1, fh - 1), R)
    page.paste(face_rgb, (x0, y0), fm)
    # bevel: a band round the face's edge, bright where it faces the light and dark where it turns away
    inner = rounded_mask((fw, fh), (5 * SS, 5 * SS, fw - 1 - 5 * SS, fh - 1 - 5 * SS), R - 5 * SS)
    band = ImageChops.subtract(fm, inner).filter(ImageFilter.GaussianBlur(1.2 * SS))
    light = diag(fw, fh, 60, 255)
    hi_l = Image.new("RGBA", (fw, fh), (255, 255, 255, 0))
    hi_l.putalpha(ImageChops.multiply(band, light.point(lambda v: max(0, v - 128) * 2)))
    lo_l = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    lo_l.putalpha(ImageChops.multiply(band, light.point(lambda v: max(0, 128 - v) * 2)))
    page.alpha_composite(hi_l, (x0, y0))
    page.alpha_composite(lo_l, (x0, y0))
    ImageDraw.Draw(page).rounded_rectangle((x0, y0, x1, y1), radius=R, outline=(70, 70, 74, 255), width=SS)
    for cx, cy in ((34, 32), (1246, 32), (34, 590), (1246, 590)):
        screw(page, cx, cy)
    return page


def screw(page, cx, cy, r=8):
    s = (r + 6) * 2 * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    R = r * SS
    sh = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((c - R + 2 * SS, c - R + 3 * SS, c + R + 2 * SS, c + R + 3 * SS), fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(1.5 * SS)))
    head = diag(2 * R, 2 * R, 110, 238)
    hm = Image.new("L", (2 * R, 2 * R), 0)
    ImageDraw.Draw(hm).ellipse((0, 0, 2 * R - 1, 2 * R - 1), fill=255)
    im.paste(Image.merge("RGB", (head,) * 3).convert("RGBA"), (int(c - R), int(c - R)), hm)
    d = ImageDraw.Draw(im)
    d.ellipse((c - R, c - R, c + R, c + R), outline=(80, 80, 84, 255), width=SS)
    for a in (35, 125):
        x0, y0 = polar(c, c, R * 0.62, a)
        x1, y1 = polar(c, c, R * 0.62, a + 180)
        d.line([(x0, y0), (x1, y1)], fill=(54, 54, 58, 255), width=int(1.8 * SS))
    page.alpha_composite(im, (int(cx * SS - c), int(cy * SS - c)))


def soft_shadow(size, box, blur=5, alpha=120, off=(0, 4), ellipse=True):
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    x0, y0, x1, y1 = box
    o = (off[0] * SS, off[1] * SS)
    (d.ellipse if ellipse else d.rounded_rectangle)((x0 + o[0], y0 + o[1], x1 + o[0], y1 + o[1]), fill=(0, 0, 0, alpha))
    return sh.filter(ImageFilter.GaussianBlur(blur * SS))


class Tab:
    def __init__(self, name, qlinks):
        self.name = name
        self.qlinks = qlinks
        self.hi = plate(W * SS, H * SS)
        self.controls = []
        self.lines = []

    @property
    def draw(self):
        return ImageDraw.Draw(self.hi)

    def text(self, x, y, s, size=17, weight="SemiBold", fill=INK, anchor="mm"):
        # printed into the metal: a faint light edge below the ink
        self.draw.text((x * SS, (y + 0.9) * SS), s, font=font(size, weight), fill=(255, 255, 255, 120), anchor=anchor)
        self.draw.text((x * SS, y * SS), s, font=font(size, weight), fill=fill, anchor=anchor)

    def line(self, x0, y0, x1, y1, w=2, fill=INK, engraved=True):
        if engraved:
            self.draw.line([((x0 + 0.8) * SS, (y0 + 1) * SS), ((x1 + 0.8) * SS, (y1 + 1) * SS)], fill=(255, 255, 255, 130),
                           width=max(1, int(round(w * SS))))
        self.draw.line([(x0 * SS, y0 * SS), (x1 * SS, y1 * SS)], fill=fill, width=max(1, int(round(w * SS))))

    def put(self, im, cx, cy):
        self.hi.alpha_composite(im, (int(round(cx * SS - im.width / 2)), int(round(cy * SS - im.height / 2))))

    def header(self, cx, cy, w, label, h=28):
        """A section's title in its outlined box (the TEMPO / WAVE / VOLUME boxes)."""
        d = self.draw
        d.rounded_rectangle(((cx - w / 2 + 0.8) * SS, (cy - h / 2 + 1) * SS, (cx + w / 2 + 0.8) * SS, (cy + h / 2 + 1) * SS), radius=7 * SS,
                            outline=(255, 255, 255, 130), width=int(2.2 * SS))
        d.rounded_rectangle(((cx - w / 2) * SS, (cy - h / 2) * SS, (cx + w / 2) * SS, (cy + h / 2) * SS), radius=7 * SS,
                            outline=INK + (255,), width=int(2.2 * SS))
        self.text(cx, cy + 1, label, 19, "Bold")

    def well(self, x0, y0, x1, y1, r=14):
        """A section recessed into the plate: a slightly darker floor, its inner shadow on the top-left edges and a
        light edge bottom-right where the plate catches the light."""
        size = self.hi.size
        box = (x0 * SS, y0 * SS, x1 * SS, y1 * SS)
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).rounded_rectangle(box, radius=r * SS, fill=255)
        floor = Image.new("RGBA", size, (0, 0, 0, 0))
        floor.putalpha(m.point(lambda v: v * 18 // 255))
        self.hi.alpha_composite(floor)
        # inner shadow: the well's mask, blurred and shifted down-right, outside of it subtracted
        sh = ImageChops.offset(m, 3 * SS, 4 * SS).filter(ImageFilter.GaussianBlur(4 * SS))
        inner = ImageChops.subtract(m, sh)
        dark = Image.new("RGBA", size, (0, 0, 0, 0))
        dark.putalpha(inner.point(lambda v: v * 110 // 255))
        self.hi.alpha_composite(dark)
        lit = Image.new("RGBA", size, (255, 255, 255, 0))
        edge = ImageChops.subtract(ImageChops.offset(m, -2 * SS, -2 * SS), m).filter(ImageFilter.GaussianBlur(0.8 * SS))
        lit.putalpha(ImageChops.subtract(m.point(lambda v: 0), edge.point(lambda v: 0)))
        hl = Image.new("L", size, 0)
        ImageDraw.Draw(hl).rounded_rectangle((box[0] + 2 * SS, box[1] + 2 * SS, box[2] + 2 * SS, box[3] + 2 * SS), radius=r * SS, outline=255, width=int(1.4 * SS))
        hl = ImageChops.subtract(hl, m)
        lit.putalpha(hl.point(lambda v: v * 150 // 255))
        self.hi.alpha_composite(lit)
        ImageDraw.Draw(self.hi).rounded_rectangle(box, radius=r * SS, outline=(96, 96, 100, 255), width=SS)

    def vrule(self, x, y0, y1):
        self.line(x, y0, x, y1, 2.2, (60, 60, 64))

    def ticks(self, cx, cy, r, n=11, major=(0, 5, 10), ring=None):
        """A pot's scale: n ticks over its travel, the ends and middle longer."""
        r0 = (ring or r) + 6
        for i in range(n):
            a = -SWEEP / 2 + SWEEP * i / (n - 1)
            long = i in major
            x0, y0 = polar(cx, cy, r0, a)
            x1, y1 = polar(cx, cy, r0 + (12 if long else 8), a)
            self.line(x0, y0, x1, y1, 2.6 if long else 2.0, INK)


# ---------------------------------------------------------------- knobs

def disc(size, box, fill_l, tint=(0, 0, 0)):
    """An RGBA disc filled with a greyscale picture (a gradient), cut to the circle in box."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    g = fill_l.resize((w, h))
    rgb = Image.merge("RGB", (g.point(lambda v: min(255, v + tint[0])), g.point(lambda v: min(255, v + tint[1])), g.point(lambda v: min(255, v + tint[2]))))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((0, 0, w - 1, h - 1), fill=255)
    im.paste(rgb.convert("RGBA"), (x0, y0), m)
    return im


def knob_sprite(r, deg):
    """The knob, hi-res RGBA, turned deg from top, lit from the top left: a knurled charcoal skirt with a bright rim
    where it meets the light and the red pointer at its edge, a stepped flat top with a sheen, and the cap's facet on one
    side of the pointer's line (it turns with the knob). The light, highlights and shading stay put as it turns."""
    R = r * SS
    s = int(2 * R + 10 * SS)
    c = s / 2
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # skirt: shaded from the light, knurls, a rim highlight on the lit side
    im.alpha_composite(disc((s, s), (c - R, c - R, c + R, c + R), diag(64, 64, 14, 70)))
    d = ImageDraw.Draw(im)
    for i in range(60):
        a = 360 * i / 60
        lit = 0.5 + 0.5 * math.cos(math.radians(a + 45))       # brighter facing the top left
        x0, y0 = polar(c, c, R * 0.78, a)
        x1, y1 = polar(c, c, R * 0.97, a)
        v = int(30 + 50 * lit)
        d.line([(x0, y0), (x1, y1)], fill=(v, v, v + 3, 255), width=max(1, int(1.3 * SS)))
    rim = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(rim).arc((c - R + SS, c - R + SS, c + R - SS, c + R - SS), start=180, end=300, fill=(230, 230, 236, 170), width=int(1.6 * SS))
    im.alpha_composite(rim.filter(ImageFilter.GaussianBlur(0.8 * SS)))
    # the step to the top: a dark ring with its shadow falling down-right
    rt = R * 0.68
    st = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(st).ellipse((c - rt + 1.5 * SS, c - rt + 3 * SS, c + rt + 1.5 * SS, c + rt + 3 * SS), fill=(0, 0, 0, 200))
    im.alpha_composite(st.filter(ImageFilter.GaussianBlur(2 * SS)))
    # the top: gradient, the turning facet, a fixed sheen
    top = disc((s, s), (c - rt, c - rt, c + rt, c + rt), diag(64, 64, 38, 92))
    facet = Image.new("L", (s, s), 0)
    ImageDraw.Draw(facet).pieslice((c - rt, c - rt, c + rt, c + rt), start=deg - 270, end=deg - 90, fill=255)
    facet = ImageChops.multiply(facet.filter(ImageFilter.GaussianBlur(0.7 * SS)), top.getchannel("A"))
    lighter = disc((s, s), (c - rt, c - rt, c + rt, c + rt), diag(64, 64, 70, 128))
    top = Image.composite(lighter, top, facet)
    im.alpha_composite(top)
    ImageDraw.Draw(im).ellipse((c - rt, c - rt, c + rt, c + rt), outline=(16, 16, 18, 255), width=SS)
    sheen = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse((c - rt * 0.78, c - rt * 0.86, c + rt * 0.05, c - rt * 0.12), fill=(255, 255, 255, 46))
    im.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(4 * SS)))
    # pointer on the skirt's rim, with a dark edge
    x0, y0 = polar(c, c, R * 0.73, deg)
    x1, y1 = polar(c, c, R * 0.97, deg)
    w = int(max(2.4, r * 0.085) * SS)
    d = ImageDraw.Draw(im)
    d.line([(x0, y0), (x1, y1)], fill=(90, 10, 8, 255), width=w + 2 * SS // 2)
    d.line([(x0, y0), (x1, y1)], fill=RED + (255,), width=w)
    return im


def knob_shadow(t, cx, cy, r):
    """The knob's shadow on the plate: a soft one cast down-right, and a tight contact one."""
    t.hi.alpha_composite(soft_shadow(t.hi.size, ((cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS), 7, 150, (5, 8)))
    t.hi.alpha_composite(soft_shadow(t.hi.size, ((cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS), 2, 170, (1, 2)))


def add_knob(t, key, cx, cy, r, name=None, ring=None, name_dy=None, ticks=11, vs=0, bw=None):
    knob_shadow(t, cx, cy, r)
    t.ticks(cx, cy, r, ticks, (0, (ticks - 1) // 2, ticks - 1), ring)
    if name:
        y = cy - (ring or r) - 34 if name_dy is None else cy + name_dy
        t.text(cx, y, name, 18)
    side = even(2 * r + 12)
    t.controls.append(dict(kind="knob", key=key, cx=cx, cy=cy, r=r, side=side, vs=vs, bw=bw or side + 20))


# ---------------------------------------------------------------- switches, buttons, LEDs

def bat_sprite(pos, size=46):
    """A bat-handle toggle seen from the front: its chrome bushing and hex nut, the lever up, mid (end-on) or down."""
    S = size * SS
    im = Image.new("RGBA", (S, int(S * 1.7)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = S / 2, im.height / 2
    # hex nut
    rn = S * 0.40
    pts = [polar(cx, cy, rn, 30 + 60 * i) for i in range(6)]
    d.polygon(pts, fill=(150, 150, 154, 255), outline=(80, 80, 84, 255))
    d.ellipse((cx - S * 0.27, cy - S * 0.27, cx + S * 0.27, cy + S * 0.27), fill=(196, 196, 200, 255), outline=(96, 96, 100, 255), width=SS)
    d.ellipse((cx - S * 0.16, cy - S * 0.16, cx + S * 0.16, cy + S * 0.16), fill=(46, 46, 50, 255))
    # lever
    lw = S * 0.30
    if pos == "mid":
        d.ellipse((cx - lw * 0.75, cy - lw * 0.75, cx + lw * 0.75, cy + lw * 0.75), fill=(20, 20, 22, 255))
        d.ellipse((cx - lw * 0.35, cy - lw * 0.55, cx + lw * 0.15, cy - lw * 0.15), fill=(90, 90, 96, 255))
    else:
        sgn = -1 if pos == "up" else 1
        L = S * 0.78
        tip = cy + sgn * L
        x0, x1 = cx - lw / 2, cx + lw / 2
        y0, y1 = min(cy, tip), max(cy, tip)
        d.rounded_rectangle((x0, y0, x1, y1), radius=lw / 2, fill=(20, 20, 22, 255))
        d.rounded_rectangle((x0 + lw * 0.18, y0 + lw * 0.3, x0 + lw * 0.42, y1 - lw * 0.3), radius=lw * 0.12, fill=(78, 78, 84, 255))
        ty = tip - sgn * lw * 0.15
        d.ellipse((cx - lw * 0.62, ty - lw * 0.5, cx + lw * 0.62, ty + lw * 0.5), fill=(26, 26, 28, 255))
    return im


def button_sprite(lit, d=40, color=RED):
    """A round red push button in a dark bezel; lit, it glows."""
    D = d * SS
    pad = 10 * SS
    s = D + 2 * pad
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    if lit:
        glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((c - D / 2 - 4 * SS, c - D / 2 - 4 * SS, c + D / 2 + 4 * SS, c + D / 2 + 4 * SS), fill=(255, 70, 50, 150))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6 * SS)))
    sh = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((c - D / 2 + 3 * SS, c - D / 2 + 5 * SS, c + D / 2 + 3 * SS, c + D / 2 + 5 * SS), fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3 * SS)))
    im.alpha_composite(disc((s, s), (c - D / 2, c - D / 2, c + D / 2, c + D / 2), diag(64, 64, 96, 236)))     # chrome bezel
    im.alpha_composite(disc((s, s), (c - D / 2 * 0.86, c - D / 2 * 0.86, c + D / 2 * 0.86, c + D / 2 * 0.86), diag(64, 64, 20, 50)))
    dr = ImageDraw.Draw(im)
    rc = D / 2 * 0.74
    base = color if lit else tuple(int(v * 0.62) for v in color)
    dr.ellipse((c - rc, c - rc, c + rc, c + rc), fill=base + (255,))
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((c - rc * 0.6, c - rc * 0.75, c + rc * 0.25, c - rc * 0.05), fill=(255, 255, 255, 120 if lit else 60))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(2 * SS)))
    return im


def led_sprite(lit, d=12):
    D = d * SS
    pad = 8 * SS
    s = D + 2 * pad
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    if lit:
        glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((c - D, c - D, c + D, c + D), fill=(255, 60, 40, 170))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4 * SS)))
    dr = ImageDraw.Draw(im)
    dr.ellipse((c - D / 2, c - D / 2, c + D / 2, c + D / 2), fill=((255, 64, 48) if lit else (128, 40, 36)) + (255,), outline=(70, 30, 28, 255), width=SS)
    dr.ellipse((c - D * 0.25, c - D * 0.3, c + D * 0.05, c - D * 0.02), fill=(255, 220, 210, 200 if lit else 60))
    return im


def add_switch(t, key, cx, cy, positions, labels=None, size=46, label_dx=34, name=None, name_dy=-78, label_side="r"):
    """A bat toggle with two or three positions (top to bottom = the parameter's options): a picture each, under clear
    segments stacked over the travel so a tap on a position's place picks it."""
    n = len(positions)
    if labels:
        ys = [cy - 30, cy, cy + 30] if n == 3 else [cy - 26, cy + 26]
        for y, s in zip(ys, labels):
            if s:
                x = cx + label_dx if label_side == "r" else cx - label_dx
                t.text(x, y, s, 15, "SemiBold", INK, "lm" if label_side == "r" else "rm")
    if name:
        for i, ln in enumerate(name.split("\n")[::-1]):
            t.text(cx, cy + name_dy - i * 19, ln, 17)
    w, h = even(size + 24), even(size * 1.7 + 12)
    # the touch segments cover the switch and its labels' side
    sw = w + (label_dx + 14 if labels else 0)
    scx = cx + ((sw - w) // 2 if label_side == "r" else -(sw - w) // 2)
    t.controls.append(dict(kind="options", key=key, cx=cx, cy=cy, w=w, h=h, n=n,
                           draw=lambda i: bat_sprite(positions[i], size), seg=(sw, h // n), seg_cx=scx))


def add_button(t, key, cx, cy, d=40, name=None, name_dy=-40):
    if name:
        t.text(cx, cy + name_dy, name, 18)
    s = d + 20
    t.controls.append(dict(kind="pair", key=key, cx=cx, cy=cy, w=even(s), h=even(s), draw=lambda st: button_sprite(st, d)))


# ---------------------------------------------------------------- frames

def crop_hi(t, cx, cy, w, h):
    x0, y0 = int(round((cx - w / 2) * SS)), int(round((cy - h / 2) * SS))
    return t.hi.crop((x0, y0, x0 + w * SS, y0 + h * SS))


def final(im, w, h):
    return im.convert("RGB").resize((w, h), Image.LANCZOS)


class Out:
    def __init__(self, root):
        self.root = root
        self.art = os.path.join(root, "art")
        shutil.rmtree(self.art, ignore_errors=True)
        os.makedirs(self.art)
        self.layout = []

    def save(self, im, name):
        im.save(os.path.join(self.art, name), optimize=True)

    def add(self, line):
        self.layout.append(line)


def default_index(params, key, n):
    p = params[key]
    if "options" in p:
        return p["options"].index(p["default"])
    return int(round((p["default"] - p["min"]) / (p["max"] - p["min"]) * (n - 1)))


def render(t, out, params, preview):
    bg = final(t.hi, W, H)
    prev = bg.convert("RGBA")
    slug = t.name.lower().replace(" ", "_")
    for c in t.controls:
        k, key = c["kind"], c["key"]
        if k == "knob":
            side, r = c["side"], c["r"]
            frames = []
            for i in range(FRAMES):
                deg = -SWEEP / 2 + SWEEP * i / (FRAMES - 1)
                bgc = crop_hi(t, c["cx"], c["cy"], side, side)
                kn = knob_sprite(r, deg)
                bgc.alpha_composite(kn, ((bgc.width - kn.width) // 2, (bgc.height - kn.height) // 2))
                frames.append(final(bgc, side, side))
            strip = Image.new("RGB", (side, side * FRAMES))
            for i, f in enumerate(frames):
                strip.paste(f, (0, i * side))
            out.save(strip, key + ".png")
            di = default_index(params, key, FRAMES)
            prev.alpha_composite(frames[di].convert("RGBA"), (int(c["cx"] - side / 2), int(c["cy"] - side / 2)))
            out.add('knob cx=%d cy=%d r=%d label="" key=%s strip=art/%s.png frames=%d ns=0 vs=%d bw=%d' %
                    (c["cx"], c["cy"] + Y_OFF, side // 2 - 6, key, key, FRAMES, c["vs"], c["bw"]))
        elif k == "pair":
            w, h = c["w"], c["h"]
            imgs = []
            for st in (0, 1):
                bgc = crop_hi(t, c["cx"], c["cy"], w, h)
                sp = c["draw"](st)
                bgc.alpha_composite(sp, ((bgc.width - sp.width) // 2, (bgc.height - sp.height) // 2))
                imgs.append(final(bgc, w, h))
            out.save(imgs[0], key + "_off.png")
            out.save(imgs[1], key + "_on.png")
            di = default_index(params, key, 2)
            prev.alpha_composite(imgs[di].convert("RGBA"), (int(c["cx"] - w / 2), int(c["cy"] - h / 2)))
            out.add('toggle cx=%d cy=%d label="" key=%s img=art/%s_off.png img_on=art/%s_on.png w=%d h=%d ns=0' %
                    (c["cx"], c["cy"] + Y_OFF, key, key, key, w, h))
        elif k == "options":
            w, h, n = c["w"], c["h"], c["n"]
            files = []
            for i in range(n):
                bgc = crop_hi(t, c["cx"], c["cy"], w, h)
                sp = c["draw"](i)
                bgc.alpha_composite(sp, ((bgc.width - sp.width) // 2, (bgc.height - sp.height) // 2))
                f = final(bgc, w, h)
                out.save(f, "%s_%d.png" % (key, i))
                files.append("art/%s_%d.png" % (key, i))
                if i == default_index(params, key, n):
                    prev.alpha_composite(f.convert("RGBA"), (int(c["cx"] - w / 2), int(c["cy"] - h / 2)))
            out.add('picture x=%d y=%d w=%d h=%d key=%s files="%s"' % (c["cx"] - w // 2, c["cy"] - h // 2 + Y_OFF, w, h, key, ",".join(files)))
            sw, sh = c["seg"]
            out.add('enum_v cx=%d cy=%d label="" key=%s options="%s" sw=%d sh=%d img=art/clear.png img_on=art/clear.png' %
                    (c["seg_cx"], c["cy"] + Y_OFF, key, ",".join([" "] * n), sw, sh))
        elif k == "picture":
            files = []
            for i, im in enumerate(c["images"]):
                bgc = crop_hi(t, c["cx"], c["cy"], c["w"], c["h"])
                bgc.alpha_composite(im, ((bgc.width - im.width) // 2, (bgc.height - im.height) // 2))
                f = final(bgc, c["w"], c["h"])
                out.save(f, "%s_%s_%d.png" % (slug, key, i))
                files.append("art/%s_%s_%d.png" % (slug, key, i))
                if i == default_index(params, key, len(c["images"])):
                    prev.alpha_composite(f.convert("RGBA"), (int(c["cx"] - c["w"] / 2), int(c["cy"] - c["h"] / 2)))
            out.add('picture x=%d y=%d w=%d h=%d key=%s files="%s"' % (c["cx"] - c["w"] // 2, c["cy"] - c["h"] // 2 + Y_OFF, c["w"], c["h"], key, ",".join(files)))
    prev.convert("RGB").save(os.path.join(preview, slug + ".png"))
    bg.save(os.path.join(out.art, slug + ".png"), optimize=True)
    if t.name == "303":
        bg.crop((40, 120, 580, 340)).resize((270, 110), Image.LANCZOS).save(os.path.join(out.art, "tile.png"))


def build(root):
    params = {p["key"]: p for p in json.load(open(os.path.join(root, "params.json")))["params"]}
    out = Out(root)
    preview = os.path.join(root, "preview")
    os.makedirs(preview, exist_ok=True)
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(os.path.join(out.art, "clear.png"))
    out.add("# generated by skin/make_skin.py: a silver panel drawn for the MPC's 1280x628 plugin area.\n"
            "theme_bg=d4d5d7\ntheme_panel=d4d5d7\ntheme_ink=222224\ntheme_ink_dim=5c5c60\ntheme_accent=de2622\n"
            "theme_accent_hi=ff4a3a\ntheme_lcd=d4d5d7\ntheme_seg_active=d4d5d7\ntheme_seg_inactive=d4d5d7\n"
            "theme_seg_active_tx=222224\ntheme_box=d4d5d7")
    import tabs
    for make in tabs.ALL:
        t = make(params)
        out.add("\n[tab %s]\nart file=art/%s.png fit=stretch" % (t.name, t.name.lower().replace(" ", "_")))
        render(t, out, params, preview)
        for l in t.lines:
            out.add(l)
        out.add('qlinks "%s" = %s' % (t.name, ",".join(t.qlinks)))
    open(os.path.join(root, "layout.conf"), "w").write("\n".join(out.layout) + "\n")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    import make_skin
    make_skin.build(sys.argv[1])
