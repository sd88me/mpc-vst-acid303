"""Model-303's two tabs, laid out for the MPC's 1280x628 plugin area (screen pixels, y from the top of the plugin area).
The synth section only: no keys, pattern or sequencer controls. Controls stay left of x ~1025, where the Q-Link
sidebar comes in."""
import make_skin as m
from make_skin import INK, DIM, Tab

K = m.add_knob
NAME = ("ACD", "303")       # the wordmark, either side of its dash


def logo(t, sub):
    # Earth Normal has no dash: the name's two halves set apart, the dash drawn between them at the letters' weight
    size = 46
    f = m.font(size, "Logo")
    x = 60
    t.text(x, 52, NAME[0], size, "Logo", INK, "lm")
    x += f.getlength(NAME[0]) / m.SS + 8
    dash = 22
    for dy, col in ((1, (255, 255, 255, 120)), (0, INK + (255,))):
        t.draw.rectangle((x * m.SS, (50 - 3.5 + dy) * m.SS, (x + dash) * m.SS, (50 + 3.5 + dy) * m.SS), fill=col)
    t.text(x + dash + 8, 52, NAME[1], size, "Logo", INK, "lm")
    t.text(62, 88, sub, 19, "Medium", DIM, "lm")


def saw_icon(t, x, y, s=9):
    t.draw.line([((x - s) * m.SS, (y + s * 0.6) * m.SS), ((x + s) * m.SS, (y - s * 0.6) * m.SS), ((x + s) * m.SS, (y + s * 0.6) * m.SS)],
                fill=INK, width=int(2.2 * m.SS))


def square_icon(t, x, y, s=9):
    p = [(x - s, y + s * 0.6), (x - s, y - s * 0.6), (x, y - s * 0.6), (x, y + s * 0.6), (x + s, y + s * 0.6), (x + s, y - s * 0.6)]
    t.draw.line([(a * m.SS, b * m.SS) for a, b in p], fill=INK, width=int(2.2 * m.SS))


def end_labels(t, cx, cy, r, lo, hi, ring=None):
    """Words at the ends of a pot's scale (SLOW/FAST, MIN/MAX)."""
    rr = (ring or r) + 28
    x0, y0 = m.polar(cx, cy, rr, -150)
    x1, y1 = m.polar(cx, cy, rr, 150)
    t.text(x0 - 4, y0 + 6, lo, 14, "SemiBold", INK)
    t.text(x1 + 4, y1 + 6, hi, 14, "SemiBold", INK)


# ------------------------------------------------------------------------------------------------ 303

def tb303(params):
    t = Tab("303", ["cutoff", "resonance", "env_mod", "decay", "accent", "tune", "volume", "waveform", "accent_hold", "quality"])
    logo(t, "CIRCUIT-MODELLED ACID BASS SYNTHESIZER")
    row = 238
    t.well(26, 124, 1024, 336)
    for x, key, name in zip([100, 270, 440, 610, 780, 950],
                            ["tune", "cutoff", "resonance", "env_mod", "decay", "accent"],
                            ["TUNE", "CUTOFF", "RESONANCE", "ENV MOD", "DECAY", "ACCENT"]):
        K(t, key, x, row, 46, name)
    # lower row: WAVE | VOLUME | ACCENT; the right-hand column (under the Q-Link sidebar when it slides in): the
    # Devil Fish's state, a tap away (its mods change what CUTOFF, ENV MOD and DECAY do), and QUALITY
    y = 492
    for x0, x1 in ((26, 290), (300, 690), (700, 1024)):
        t.well(x0, 354, x1, 578)
    t.well(1040, 124, 1252, 336)
    t.well(1040, 354, 1252, 578)
    t.header(150, 384, 170, "WAVE")
    m.add_switch(t, "waveform", 132, y, ["up", "down"])
    saw_icon(t, 170, y - 26)
    square_icon(t, 170, y + 26)
    t.header(500, 384, 280, "VOLUME")
    K(t, "volume", 500, y - 4, 56, ring=56)
    end_labels(t, 500, y - 4, 56, "MIN", "MAX")
    t.header(860, 384, 200, "ACCENT")
    m.add_button(t, "accent_hold", 860, y, 46)
    t.text(860, y + 46, "HOLD", 14, "SemiBold", DIM)
    t.header(1146, 160, 180, "DEVIL FISH")
    m.add_button(t, "devil_fish", 1146, 238, 46)
    t.text(1146, 284, "MODS ON", 14, "SemiBold", DIM)
    t.header(1146, 384, 180, "QUALITY")
    m.add_switch(t, "quality", 1126, y, ["up", "mid", "down"], ["HQ", "AUTO", "ECO"], label_dx=30)
    return t


# ------------------------------------------------------------------------------------------------ DEVIL FISH

def devil_fish(params):
    t = Tab("DEVIL FISH", ["soft_attack", "normal_decay", "accent_decay", "filter_tracking", "overdrive", "filter_fm", "slide_time",
                           "devil_fish", "sweep_speed", "accent_sweep", "muffler", "sub_osc", "sub_level", "vco"])
    logo(t, "DEVIL FISH MODS  -  OFF: THE STANDARD 303")
    # the mods' master switch, in the right-hand column: a red button, lit while they're in
    t.well(1040, 124, 1252, 336)
    t.well(1040, 354, 1252, 578)
    t.header(1146, 160, 180, "DEVIL FISH")
    m.add_button(t, "devil_fish", 1146, 238, 52)
    t.text(1146, 290, "ON / OFF", 14, "SemiBold", DIM)
    row = 238
    t.well(26, 124, 1024, 336)
    K(t, "soft_attack", 100, row, 46, "SOFT ATTACK")
    K(t, "normal_decay", 270, row, 46)
    K(t, "accent_decay", 440, row, 46)
    t.text(355, row - 80, "NORMAL  —  DECAY  —  ACCENT", 18)
    K(t, "filter_tracking", 610, row, 46, "FILTER TRACKING")
    K(t, "overdrive", 780, row, 46, "OVERDRIVE")
    K(t, "filter_fm", 950, row, 46, "FILTER FM")
    # lower row: SLIDE TIME | SWEEP SPEED, ACCENT SWEEP | MUFFLER | SUB OSC | VCO
    y = 492
    for x0, x1 in ((26, 182), (192, 462), (472, 632), (642, 1024)):
        t.well(x0, 354, x1, 578)
    K(t, "slide_time", 100, y, 44, "SLIDE TIME", name_dy=-82)
    m.add_switch(t, "sweep_speed", 285, y, ["up", "mid", "down"], ["FAST", "NORM", "SLOW"], label_dx=30, label_side="l",
                 name="SWEEP\nSPEED", name_dy=-62)
    m.add_switch(t, "accent_sweep", 395, y, ["up", "mid", "down"], ["2", "1", "0"], label_dx=28, name="ACCENT\nSWEEP", name_dy=-62)
    t.text(395, y + 64, "1, 0: HI RES", 14, "SemiBold", DIM)
    m.add_switch(t, "muffler", 550, y, ["up", "mid", "down"], ["2", "1", "0"], label_dx=28, name="MUFFLER", name_dy=-62)
    t.header(830, 384, 260, "SUB OSC")
    m.add_button(t, "sub_osc", 760, y + 4, 44)
    m.add_switch(t, "sub_level", 880, y, ["up", "mid", "down"], ["HIGH", "MID", "LOW"], label_dx=28)
    t.header(1146, 384, 180, "VCO")
    m.add_switch(t, "vco", 1131, y, ["up", "down"], ["ON", "OFF"], label_dx=28)
    return t


ALL = [tb303, devil_fish]
