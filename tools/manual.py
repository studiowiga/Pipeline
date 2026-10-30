# PIPELINE (Studio Wiga) - notice PDF bilingue (anglais puis francais), illustree avec le rendu reel du plugin.
# Usage : python3 tools/manual.py <dossier des captures (tools/render)> <fichier PDF de sortie>
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, CondPageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[1]
OUT = sys.argv[2]
VERSION = "1.4.0"
TMP = os.path.dirname(os.path.abspath(OUT))
FONTS = os.path.join(ROOT, "assets", "fonts")

for n, f in (("Pop", "Poppins-Regular"), ("PopL", "Poppins-Light"), ("PopM", "Poppins-Medium"), ("PopB", "Poppins-Bold"),
             ("Bebas", "BebasNeue-Regular")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(FONTS, f + ".ttf")))

ACC = colors.HexColor("#1F86C8"); ACC_L = colors.HexColor("#5FD0FF")       # bleu de la LED et du boitier
DARK = colors.HexColor("#1B1C20"); GREY = colors.HexColor("#686A72"); LIGHT = colors.HexColor("#EEF2F5")
ACC_RGB = (31, 134, 200)

LAY = json.load(open(os.path.join(ROOT, "tools", "layout.json")))

def shot(name): return Image.open(os.path.join(SHOTS, name)).convert("RGB")
K = shot("pipeline_full.png").height / 958.0          # px par unite 760 x 958

# ---------- capture annotee ----------
src = shot("pipeline_full.png")
ann = src.copy(); dr = ImageDraw.Draw(ann)
fnt = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 30)
marks = [  # numero, x, y (unites)
    (1, 164, 134), (2, 600, 134), (3, 470, 318), (4, 612, 701), (5, 612, 751),
    (6, 420, 70), (7, 462, 860), (8, 72, 520), (9, 690, 520)]
for n, x, y in marks:
    cx, cy, r = x * K, y * K, 24
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=ACC_RGB, width=5)
    dr.text((cx, cy + 1), str(n), font=fnt, fill=(27, 28, 32), anchor="mm")
annotated = os.path.join(TMP, "pipeline_annotated.png"); ann.save(annotated)

def crop_u(img_, box):
    k = img_.height / 958.0
    return img_.crop(tuple(int(v * k) for v in box)).resize((int((box[2] - box[0]) * 2), int((box[3] - box[1]) * 2)), Image.LANCZOS)
def strip(images, path, gap=16):
    h = max(i.height for i in images)
    s = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), h), (255, 255, 255))
    x = 0
    for i in images: s.paste(i, (x, 0)); x += i.width + gap
    s.save(path); return path

knobs_img = strip([crop_u(shot("pipeline_full.png"), (150, 112, 610, 300))], os.path.join(TMP, "pipeline_knobs.png"))
mode_img = strip([crop_u(shot("pipeline_full.png"), (262, 300, 504, 502)), crop_u(shot("pipeline_envp.png"), (262, 300, 504, 502))],
                 os.path.join(TMP, "pipeline_mode.png"))
fs_img = strip([crop_u(shot("pipeline_bypass.png"), (316, 778, 446, 904)), crop_u(shot("pipeline_full.png"), (316, 778, 446, 904)),
                crop_u(shot("pipeline_pressed.png"), (316, 778, 446, 904))], os.path.join(TMP, "pipeline_fs.png"))
disp_img = strip([crop_u(shot(p), (170, 660, 592, 784)) for p in ("pipeline_full.png", "pipeline_envp.png")], os.path.join(TMP, "pipeline_disp.png"), gap=10)
disp2_img = strip([crop_u(shot(p), (170, 660, 592, 784)) for p in ("pipeline_status.png", "pipeline_sync.png")], os.path.join(TMP, "pipeline_disp2.png"), gap=10)

# ---------- couverture : pedale detouree, reflet au sol, halo bleu tres doux ----------
cov = shot("pipeline_full.png")
msk = Image.open(os.path.join(ROOT, "tools", "pedal_mask.png")).convert("L").resize(cov.size, Image.LANCZOS)
cut = Image.new("RGBA", cov.size, (0, 0, 0, 0)); cut.paste(cov, (0, 0), msk)
cut = cut.crop(cut.getbbox())
cw, ch = cut.size
pad = int(cw * 0.16)
canvas = Image.new("RGBA", (cw + 2 * pad, int(ch * 1.30) + pad), (0, 0, 0, 255))
yy, xx = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float64)
gcx, gcy = canvas.width / 2, pad + ch * 0.42
glow = np.exp(-(((xx - gcx) / (cw * 0.62)) ** 2 + ((yy - gcy) / (ch * 0.48)) ** 2)) * 30
edge = np.clip(np.minimum.reduce([xx, canvas.width - 1 - xx, yy, canvas.height - 1 - yy]) / (pad * 0.9), 0, 1)
glow *= edge ** 2
halo = np.dstack([glow * 0.20, glow * 0.62, glow * 1.0, np.full_like(glow, 255)]).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(halo, "RGBA"))
refl = cut.transpose(Image.FLIP_TOP_BOTTOM)
ra = np.array(refl).astype(np.float64)
fade = np.clip(1 - np.arange(refl.height) / (refl.height * 0.22), 0, 1) ** 1.6 * 0.22
ra[..., 3] *= fade[:, None]
canvas.alpha_composite(Image.fromarray(ra.astype(np.uint8), "RGBA"), (pad, pad + ch + 6))
canvas.alpha_composite(cut, (pad, pad))
canvas = canvas.crop((0, 0, canvas.width, pad + int(ch * 1.20)))
cover = os.path.join(TMP, "pipeline_cover_cutout.png"); canvas.convert("RGB").save(cover)

def img(path, width):
    im = Image.open(path); h = width * im.height / im.width
    return RLImage(path, width=width, height=h)

# ---------- styles ----------
st = {
    "h1": ParagraphStyle("h1", fontName="PopB", fontSize=20, leading=24, textColor=ACC, spaceAfter=8, spaceBefore=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="PopM", fontSize=13, leading=17, textColor=DARK, spaceAfter=4, spaceBefore=10, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Pop", fontSize=9.6, leading=14, textColor=DARK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Pop", fontSize=8.2, leading=11.5, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Pop", fontSize=8.4, leading=11, textColor=DARK),
    "cellb": ParagraphStyle("cellb", fontName="PopM", fontSize=8.4, leading=11, textColor=DARK),
    "cover": ParagraphStyle("cover", fontName="Bebas", fontSize=54, leading=58, textColor=colors.white, alignment=TA_CENTER),
    "coversub": ParagraphStyle("coversub", fontName="Pop", fontSize=12, leading=16, textColor=colors.HexColor("#BDBDBA"), alignment=TA_CENTER),
    "coverlang": ParagraphStyle("coverlang", fontName="PopM", fontSize=8.5, leading=11, textColor=ACC_L),
}
def P(t, s="p"): return Paragraph(t, st[s])
def bullets(items): return [P("&bull;&nbsp;&nbsp;" + i) for i in items]
def table(rows, widths, header=True):
    data = [[P(c, "cellb" if (header and r == 0) else "cell") for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9D6")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header: style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACC)]
    t.setStyle(TableStyle(style)); return t

# ---------- donnees (identiques au code livre : PluginProcessor.cpp, PipelineDSP.h) ----------
MODES = ["SINE", "TRIANGLE", "RAMP", "SQUARE", "RANDOM", "ENV D", "ENV R", "ENV P"]
FACTORY = [  # nom, rate, depth, mode
    ("Smooth Sine Wave", 4.0, 4.0, 0), ("Haunting Ramp (High Rate)", 7.5, 5.0, 2), ("Chooglin' Amp Vibrato", 6.5, 3.0, 0),
    ("Seasick Sine", 2.5, 7.5, 0), ("Triangle Wobble", 5.0, 5.0, 1), ("Sonar Ping", 3.5, 6.5, 2), ("Hammer-On Trill", 6.5, 6.0, 3),
    ("Kosmische Pulse", 4.0, 3.5, 3), ("Warped Record", 3.0, 2.0, 4), ("Drunken Master", 5.0, 8.5, 4), ("Motorik Dig-In", 6.0, 6.0, 5),
    ("Touch Rate Ripple", 5.5, 4.5, 6), ("My Bloody Valentine", 6.0, 10.0, 7), ("Touch Chorus", 3.0, 5.0, 7), ("Pseudo Flange", 1.5, 5.0, 7)]
def hz(v): return 0.1 * 160 ** ((v / 10.0) ** 0.8)
def pc(v): return f"{round(v * 10)} %"
def rate_s(v, mode, lang):
    if mode == 6: return pc(v) + (" (sens.)" if lang == "en" else " (sensib.)")
    if mode == 7: return pc(v) + (" (range)" if lang == "en" else " (amplitude)")
    h = hz(v)
    s = f"{h:.2f}" if h < 1 else f"{h:.1f}"
    return pc(v) + "<br/>(" + (s if lang == "en" else s.replace(".", ",")) + " Hz)"
def depth_s(v, mode, lang):
    if mode == 5: return pc(v) + (" (sens.)" if lang == "en" else " (sensib.)")
    if mode == 7:
        w = round(v * 10)
        return ("all wet" if lang == "en" else "tout traité") if w >= 100 else f"{100 - w} / {w}"
    return pc(v)
FACT_DESC = {
 "en": ["The first suggested setting of the original manual: a smooth, classic vibrato.",
        "The second suggested setting of the original manual: sonar pings at a high rate.",
        "Faster, shallower sine: the amp-style vibrato of swamp rock.",
        "Slow and deep: the pitch rolls like a boat at sea.",
        "Sharper turns at the top and bottom of each cycle than the sine.",
        "A slow ramp: a sharp upward ping, then a fast drop and a long sustain.",
        "Square wave: two pitches and an instant jump between them, a trill without hammer-ons.",
        "Slower square, shallower: steady kosmische pulsations.",
        "Random at low depth: the wow of a warped record.",
        "Random at high depth: unpredictable, greasy pitch bends.",
        "Env D: the harder you pick, the deeper the vibrato. For motorik grooves.",
        "Env R: the harder you pick, the faster the vibrato.",
        "Env P all wet: every attack dips the pitch like a tremolo arm, then it floats back.",
        "Env P at noon: 50/50 dry / wet, touch-sensitive chorus.",
        "Env P with a short range at 50/50: dynamic pseudo-flange."],
 "fr": ["Le premier réglage conseillé du manuel d'origine : un vibrato doux et classique.",
        "Le deuxième réglage conseillé du manuel d'origine : des « pings » de sonar à vitesse élevée.",
        "Sinus plus rapide et moins profond : le vibrato d'ampli du swamp rock.",
        "Lent et profond : la hauteur tangue comme un bateau.",
        "Des virages plus francs en haut et en bas de chaque cycle que le sinus.",
        "Une rampe lente : un « ping » vers le haut, puis une descente rapide et un long palier.",
        "Onde carrée : deux hauteurs et un saut instantané entre elles, un trille sans hammer-on.",
        "Carré plus lent et moins profond : des pulsations kosmische régulières.",
        "Random à faible Depth : le pleurage d'un disque voilé.",
        "Random à forte Depth : des glissandos imprévisibles et « graisseux ».",
        "Env D : plus on attaque fort, plus le vibrato est profond. Pour les grooves motorik.",
        "Env R : plus on attaque fort, plus le vibrato est rapide.",
        "Env P tout traité : chaque attaque fait plonger la hauteur comme un levier de vibrato, puis elle remonte.",
        "Env P à midi : 50/50 sec / traité, un chorus sensible au toucher.",
        "Env P avec une petite amplitude à 50/50 : un pseudo-flanger dynamique."],
}
DIVS = "4 bars, 2 bars, 1 bar, 1/2, 1/4 D, 1/2 T, 1/4, 1/8 D, 1/4 T, 1/8, 1/8 T, 1/16, 1/16 T, 1/32"

T = {}
T["en"] = dict(
 lang="ENGLISH", sub="8-mode pitch vibrato", ver="User manual · version " + VERSION,
 intro_t="1. Introduction",
 intro=["<b>Pipeline</b> is a Studio Wiga VST3 plugin modelled on the <b>EarthQuaker Devices Aqueduct</b> vibrato: same controls (RATE, DEPTH and an 8-position MODE selector), same eight modulation modes from \"not that weird\" to \"wow, that's weird\", and the same Flexi-Switch footswitch.",
        "Like the pedal, Pipeline is a true pitch vibrato: the guitar goes through a very short delay line whose length is modulated, so you hear a change of pitch (not of volume, which would be a tremolo). In the waveform modes the signal is 100 % wet, like the original; only <b>Env P</b> has a dry / wet mix.",
        "Pipeline was built from the original manual, the manufacturer's page and reviews (Premier Guitar, MusicRadar, Guitar World, Bonedo). The shape of each mode was designed as the shape of the <b>pitch</b> movement you hear, then measured on test signals."],
 inst_t="2. Installation",
 inst=[("Windows", "Copy <b>Pipeline.vst3</b> to <b>C:\\Program Files\\Common Files\\VST3</b>. In Reaper: Options &gt; Preferences &gt; Plug-ins &gt; VST &gt; <i>Re-scan</i>. The plugin appears as <b>Pipeline (Studio Wiga)</b>."),
       ("macOS", "Unzip the archive and copy <b>Pipeline.vst3</b> to <b>/Library/Audio/Plug-Ins/VST3</b> (or ~/Library/Audio/Plug-Ins/VST3). The build is universal (Apple Silicon and Intel) and ad hoc signed; if macOS blocks it, run <i>xattr -cr</i> on the file. Then re-scan in Reaper.")],
 ov_t="3. Interface overview",
 ov_rows=[["#", "Control", "Role"], ["1", "RATE", "LFO speed (in Env R: envelope sensitivity; in Env P: bend sensitivity and range)"],
          ["2", "DEPTH", "Vibrato intensity (in Env D: envelope sensitivity; in Env P: dry / wet mix)"],
          ["3", "MODE", "8 positions: SINE, TRI, RAMP, SQR, RAND, ENV D, ENV R, ENV P"],
          ["4", "Display", "Left: value of the control you touch, otherwise the mode, speed and live pitch deviation. Right: live scope of the pitch modulation"],
          ["5", "Preset bar", "Arrows = previous / next preset, name = preset menu"],
          ["6", "LED", "Effect on (large blue LED); its light falls on the panel"],
          ["7", "Footswitch", "Flexi-Switch: tap = on / off, hold = momentary"],
          ["8 / 9", "OUT / IN", "Output on the left, input on the right, as on a real pedal"]],
 ctl_t="4. Controls",
 ctl=[("RATE", "Speed of the LFO, i.e. how fast the pitch rises and falls: 0.1 Hz fully counter-clockwise, about 1.8 Hz at 12 o'clock, 5.6 Hz at 3 o'clock, 16 Hz fully clockwise. In <b>Env R</b> it becomes the sensitivity of the envelope; in <b>Env P</b> the sensitivity and overall range of the pitch bend. With <b>tempo sync</b> on, RATE chooses a note value instead (see section 6)."),
      ("DEPTH", "Intensity of the vibrato (amplitude of the LFO). The curve is progressive: a light shimmer up to 11 o'clock, a classic vibrato around noon, seasick bends beyond. As on any delay-line vibrato, the same DEPTH gives more pitch change at a higher RATE; at extreme settings the deviation is held around +4 / -6 semitones so the sound never turns inside out. In <b>Env D</b>, DEPTH becomes the envelope sensitivity; in <b>Env P</b>, the dry / wet mix."),
      ("Turning the knobs", "Drag up / right to increase; Shift for fine adjustment; mouse wheel; double-click returns to 12 o'clock. These are the knurled knobs of Holyverb: the knurling turns with the knob, the white index and dot follow the exact angle, while the reflections and the shadow stay still, lit from the top left like the rest of the pedal.")],
 knobs_cap="RATE and DEPTH: the knurled knobs of Holyverb.",
 modes_t="5. The eight modes",
 modes_intro="As in the original manual, the modes are listed from \"not that weird\" to \"wow, that's weird\". Click the MODE knob and drag, use the mouse wheel, or click directly on a label around the selector. The label of the selected mode lights up in blue, like LED lettering.",
 modes=[["Mode", "What you hear", "RATE", "DEPTH"],
        ["SINE", "Smooth, rolling pitch: the classic amp vibrato.", "Speed", "Intensity"],
        ["TRIANGLE", "Sharper rise and fall than the sine, a more pronounced bend at the peak of each cycle.", "Speed", "Intensity"],
        ["RAMP", "A sharp \"sonar\" ping upward, a fast downward slope, then a synth-like sustain and release.", "Speed", "Intensity"],
        ["SQUARE", "Two pitches with an almost instant jump between them: trills without hammer-ons and pull-offs.", "Speed", "Interval"],
        ["RANDOM", "Warped-record wow at low DEPTH, increasingly drunken and random pitch bends as DEPTH rises.", "Speed", "Intensity and randomness"],
        ["ENV D", "Sine LFO whose intensity follows your pick attack: the harder you dig in, the deeper the vibrato.", "Speed", "Envelope sensitivity"],
        ["ENV R", "Sine vibrato whose speed follows your attack: about 0.35 Hz at rest, up to 13 Hz when you hit hard.", "Envelope sensitivity", "Intensity"],
        ["ENV P", "\"My Bloody Valentine\" mode: each attack makes the pitch dip, like a tremolo arm, then float back. The only mode with a dry signal.", "Bend sensitivity and range", "Dry / wet mix"]],
 envp=["<b>Env P mix</b>: DEPTH fully counter-clockwise = all dry, 12 o'clock = 50 / 50 with a small amount of phase cancellation (touch-sensitive chorus, pseudo-flange), fully clockwise = all wet (pure pitch dips). Above noon the dry signal is gradually removed.",
       "<b>Envelope modes</b>: as the original manual advises, place Pipeline first in the chain, before anything that adds gain. It is tuned for low- to medium-output pickups; with hot pickups lower the sensitivity (RATE in Env R and Env P, DEPTH in Env D)."],
 mode_cap="The MODE selector (Sine, then Env P): it turns step by step to its new position and the label of the selected mode lights up in blue.",
 fs_t="6. Footswitch, LED and tempo sync",
 fs=["<b>Flexi-Switch</b> (as on the Aqueduct): a short click switches the effect on or off. Press and hold while the effect is off and it works as a momentary switch: the effect is on while you hold it and switches off when you release (after about 0.45 s). The button darkens while it is pressed. This behaviour can be switched off in right-click &gt; <b>Settings</b> &gt; <b>Flexi-Switch: hold = momentary</b>.",
     "Bypass and switching use a short 12 ms crossfade (no click), like the pedal's silent relay switching. The <b>LED</b> fades on and off and lights the panel around it.",
     "<b>Tempo sync</b> (right-click &gt; <b>Tempo sync</b>): the LFO follows the DAW tempo and RATE chooses a note value for one cycle: " + DIVS + " (D = dotted, T = triplet). When the transport is playing, the LFO phase is locked to the bars. Tempo sync applies to Sine, Triangle, Ramp, Square, Random and Env D. Without a host tempo, the display shows NO TEMPO and RATE works normally.",
     "Every parameter can be automated in the DAW (Rate, Depth, Mode, Tempo Sync, Footswitch, Flexi-Switch, MIDI footswitch mode)."],
 fs_cap="Footswitch: bypass (LED off), effect on, pressed (button darkened).",
 midi_t="7. MIDI",
 midi_txt=["<b>MIDI Learn on every control</b>: right-click RATE, DEPTH, MODE or the footswitch. The top of the menu shows <b>MIDI Learn: &lt;Name&gt; (CC n / none)</b> with the current assignment, <b>Clear MIDI: &lt;Name&gt;</b> and, while a learn is waiting, <b>Cancel MIDI learn</b>. Then move a pedal or knob or press a footswitch on your controller: the display shows <b>MIDI LEARN: move a control for &lt;Name&gt;</b>, then <b>&lt;Name&gt; = CC n</b> for 2 seconds.",
           "Every right-click menu also has the <b>MIDI map</b> submenu: <b>Learn</b> for each of the 5 controls (Tempo Sync included), <b>Cancel MIDI learn</b> and <b>Reset MIDI to defaults (CC 20-24)</b>. A CC number can only drive one control. Learn accepts CC 0 to 119; Pipeline listens on all channels. <b>Assignments are saved with the project.</b>"],
 midi_hdr=["Control", "Default CC", "Type"],
 midi=[["Rate", "CC 20", "Continuous 0-127; 14-bit with CC 52"], ["Depth", "CC 21", "Continuous 0-127; 14-bit with CC 53"],
       ["Mode", "CC 22", "8-position selector: 0-127 split into 8 equal zones (Sine to Env P)"],
       ["Tempo Sync", "CC 23", "Switch: 64 and above = ON"],
       ["Footswitch", "CC 24", "Each press toggles on / off (default, for momentary footswitches such as the M-Vave Chocolate) or latching (127 = on / 0 = off)"]],
 midi2=["<b>MIDI footswitch mode</b>: right-click &gt; <b>Settings</b> &gt; <b>MIDI footswitch: each press toggles on / off</b> (default: one press = on, next press = off, no need to hold) or <b>MIDI footswitch latching (127 = on / 0 = off)</b> for latching switches.",
        "<b>Expression pedals</b> on RATE or DEPTH are smoothed (ramp between two messages, then a 2-pole smoothing), 14-bit CC accepted, pedal travel learnt automatically (0 and 100 % reached even if the pedal only sends 2-116) and small dead zones at both ends. A pedal on RATE in Env P becomes a real-time bend range control.",
        "<b>Program Change</b> 1-15 loads the factory presets."],
 win_t="8. Window and display",
 win=["Right-click &gt; <b>Window size</b>: <b>60 % (default)</b>, <b>75 %</b>, <b>100 %</b>. The window opens at the same default size as the other Studio Wiga single pedals and can never be made smaller; drag the corner to enlarge it (proportions locked).",
      "The left part of the display shows the value of the control you just moved for 2.5 s, with its meaning in the current mode (for example <b>RATE (BEND RANGE)</b> in Env P, <b>DEPTH (MIX) 50 / 50</b>). The rest of the time it shows the mode, the LFO speed and the live pitch deviation in cents (the bend depth in Env P).", "<b>Scope</b>: the right part of the display draws the pitch modulation as it happens (animated, 30 frames per second), scrolling from right to left: the right edge is what you hear now. RATE changes the number of cycles, DEPTH the height, MODE the shape (sine, triangle, sonar ramp, square, random). In the envelope modes it follows your playing: the wave swells (Env D), speeds up (Env R) or dips like a tremolo arm (Env P) with each attack, and stays flat while nothing is played. In bypass the trace goes flat and dim."],
 disp_cap="Display: live information and scope (Sine, Env P), then the value of the control being moved (Rate in Hz, Rate in tempo sync).",
 pre_t="9. Presets",
 pre=["15 factory presets are included (also in the DAW preset menu and on MIDI Program Change). The first two are the \"Suggested Settings\" of the original manual. Nine user slots can be saved from the preset menu (they store Rate, Depth, Mode and Tempo Sync)."],
 fac_hdr=["#", "Preset", "Mode", "Rate", "Depth", "Description"],
 tips_t="10. Playing tips",
 tips=["In Reaper put Pipeline first, before Two Notes Genome or any amp simulator: the envelope modes need the clean, dynamic guitar signal, and a vibrato in front of the amp sounds like the pedal on a pedalboard.",
       "Env P with Flexi-Switch: hold the footswitch only on the chords you want to warp, for Kevin Shields style glide guitar.",
       "Low tunings: Pipeline has no pitch detection, so a 7-string in G or any lower tuning works without limit. On low notes keep DEPTH a little lower: the same deviation in cents is more audible as beating on a big low chord.",
       "Put an expression pedal on DEPTH in Sine or Triangle to fade the vibrato in at the end of held notes, or on RATE to speed up a Leslie-like wobble.",
       "Square at a high RATE and low DEPTH becomes a fast, flutter-like texture; Random at minimum DEPTH adds a subtle tape-wow to clean arpeggios."],
 tech_t="11. Technical specifications",
 tech=[["Format", "VST3, Windows (x64) and macOS (Apple Silicon + Intel)"], ["Channels", "Mono or stereo (the same modulation on both channels)"],
       ["Engine", "Modulated delay line with 4-point Hermite interpolation, pitch-shaped LFO tables, envelope follower (1.5 ms attack, 140 ms release), 7.2 kHz 2-pole low-pass and gentle saturation on the wet path, read-head crossfade on mode and preset changes"],
       ["Delay", "0.6 ms minimum plus half the modulation swing (up to about 11 ms at full DEPTH and slow RATE); no latency is reported to the host, as with a hardware vibrato (the original measured about 52 ms)"],
       ["Pitch range", "Up to about +4 / -6 semitones (slew limiter: never reversed playback)"],
       ["Sample rates", "44.1 to 192 kHz"], ["Version", VERSION],
       ["Window", "60 % (default, also the minimum size), 75 %, 100 %; anti-freeze v2 on Windows (software rendering, display caches rebuilt by a timer, redraw watchdog, no call to the host from the audio thread)"],
       ["MIDI", "MIDI Learn on 5 controls (saved with the project), defaults CC 20-24 (14-bit on CC 52-53), Program Change 1-15, all channels"]],
)
T["fr"] = dict(
 lang="FRANÇAIS", sub="Vibrato de hauteur à 8 modes", ver="Notice d'utilisation · version " + VERSION,
 intro_t="1. Présentation",
 intro=["<b>Pipeline</b> est un plugin VST3 Studio Wiga qui reprend le vibrato <b>EarthQuaker Devices Aqueduct</b> : mêmes commandes (RATE, DEPTH et un sélecteur MODE à 8 positions), mêmes huit modes de modulation, du « pas si bizarre » au « franchement bizarre », et même footswitch Flexi-Switch.",
        "Comme la pédale, Pipeline est un vrai vibrato de hauteur : la guitare passe dans une ligne de retard très courte dont la longueur est modulée, on entend donc une variation de hauteur (et non de volume, ce serait un trémolo). Dans les modes à forme d'onde, le signal est 100 % traité, comme sur l'original ; seul <b>Env P</b> a un mélange sec / traité.",
        "Pipeline a été construit d'après le manuel d'origine, la page du fabricant et les tests (Premier Guitar, MusicRadar, Guitar World, Bonedo). La forme de chaque mode a été dessinée comme la forme du mouvement de <b>hauteur</b> que l'on entend, puis mesurée sur des signaux de test."],
 inst_t="2. Installation",
 inst=[("Windows", "Copiez <b>Pipeline.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>. Dans Reaper : Options &gt; Preferences &gt; Plug-ins &gt; VST &gt; <i>Re-scan</i>. Le plugin apparaît sous le nom <b>Pipeline (Studio Wiga)</b>."),
       ("macOS", "Décompressez l'archive et copiez <b>Pipeline.vst3</b> dans <b>/Library/Audio/Plug-Ins/VST3</b> (ou ~/Library/Audio/Plug-Ins/VST3). La version est universelle (Apple Silicon et Intel) et signée localement ; si macOS la bloque, lancez <i>xattr -cr</i> sur le fichier. Relancez ensuite le scan dans Reaper.")],
 ov_t="3. Vue d'ensemble",
 ov_rows=[["N°", "Commande", "Rôle"], ["1", "RATE", "Vitesse du LFO (en Env R : sensibilité de l'enveloppe ; en Env P : sensibilité et amplitude du bend)"],
          ["2", "DEPTH", "Intensité du vibrato (en Env D : sensibilité de l'enveloppe ; en Env P : mélange sec / traité)"],
          ["3", "MODE", "8 positions : SINE, TRI, RAMP, SQR, RAND, ENV D, ENV R, ENV P"],
          ["4", "Écran", "À gauche : valeur de la commande touchée, sinon le mode, la vitesse et l'écart de hauteur en direct. À droite : courbe de la modulation en direct"],
          ["5", "Barre de presets", "Flèches = preset précédent / suivant, nom = menu des presets"],
          ["6", "LED", "Effet en marche (grosse LED bleue) ; sa lumière éclaire la façade"],
          ["7", "Footswitch", "Flexi-Switch : appui bref = marche / arrêt, appui maintenu = momentané"],
          ["8 / 9", "OUT / IN", "Sortie à gauche, entrée à droite, comme sur une vraie pédale"]],
 ctl_t="4. Les commandes",
 ctl=[("RATE", "Vitesse du LFO, c'est-à-dire la rapidité avec laquelle la hauteur monte et descend : 0,1 Hz tout à gauche, environ 1,8 Hz à 12 h, 5,6 Hz à 15 h, 16 Hz tout à droite. En <b>Env R</b>, il devient la sensibilité de l'enveloppe ; en <b>Env P</b>, la sensibilité et l'amplitude générale du bend. Avec la <b>synchro tempo</b>, RATE choisit une valeur de note (voir section 6)."),
      ("DEPTH", "Intensité du vibrato (amplitude du LFO). La course est progressive : léger frémissement jusqu'à 11 h, vibrato classique vers midi, tangage au-delà. Comme sur tout vibrato à ligne de retard, un même DEPTH donne plus d'écart de hauteur quand RATE est plus élevé ; aux réglages extrêmes, l'écart est tenu vers +4 / -6 demi-tons pour que le son ne se retourne jamais. En <b>Env D</b>, DEPTH devient la sensibilité de l'enveloppe ; en <b>Env P</b>, le mélange sec / traité."),
      ("Tourner les potards", "Tirez vers le haut / la droite pour augmenter ; Maj = réglage fin ; molette ; double-clic = retour à 12 h. Ce sont les potards moletés de Holyverb : le moletage tourne avec le potard, l'index blanc et le point suivent l'angle exact, tandis que les reflets et l'ombre restent fixes, éclairés depuis le haut à gauche comme le reste de la pédale.")],
 knobs_cap="RATE et DEPTH : les potards moletés de Holyverb.",
 modes_t="5. Les huit modes",
 modes_intro="Comme dans le manuel d'origine, les modes sont classés du « pas si bizarre » au « franchement bizarre ». Cliquez sur le sélecteur MODE et tirez, utilisez la molette, ou cliquez directement sur une étiquette autour du sélecteur. L'étiquette du mode choisi s'allume en bleu, comme une écriture LED.",
 modes=[["Mode", "Ce qu'on entend", "RATE", "DEPTH"],
        ["SINE", "Hauteur qui ondule en douceur : le vibrato d'ampli classique.", "Vitesse", "Intensité"],
        ["TRIANGLE", "Montée et descente plus franches que le sinus, un bend plus marqué au sommet de chaque cycle.", "Vitesse", "Intensité"],
        ["RAMP", "Un « ping » de sonar vers le haut, une descente rapide, puis un palier et un retour façon synthé.", "Vitesse", "Intensité"],
        ["SQUARE", "Deux hauteurs et un saut presque instantané entre elles : des trilles sans hammer-on ni pull-off.", "Vitesse", "Intervalle"],
        ["RANDOM", "Pleurage de disque voilé à faible DEPTH, glissandos de plus en plus ivres et aléatoires en montant DEPTH.", "Vitesse", "Intensité et désordre"],
        ["ENV D", "LFO sinus dont l'intensité suit l'attaque : plus on attaque fort, plus le vibrato est profond.", "Vitesse", "Sensibilité de l'enveloppe"],
        ["ENV R", "Vibrato sinus dont la vitesse suit l'attaque : environ 0,35 Hz au repos, jusqu'à 13 Hz en attaquant fort.", "Sensibilité de l'enveloppe", "Intensité"],
        ["ENV P", "Mode « My Bloody Valentine » : chaque attaque fait plonger la hauteur, comme un levier de vibrato, puis elle remonte. Seul mode avec signal sec.", "Sensibilité et amplitude du bend", "Mélange sec / traité"]],
 envp=["<b>Mélange en Env P</b> : DEPTH tout à gauche = tout sec, 12 h = 50 / 50 avec un peu d'annulation de phase (chorus sensible au toucher, pseudo-flanger), tout à droite = tout traité (plongées de hauteur pures). Au-delà de midi, le signal sec diminue progressivement.",
       "<b>Modes d'enveloppe</b> : comme le conseille le manuel d'origine, placez Pipeline en premier dans la chaîne, avant tout ce qui ajoute du gain. Il est réglé pour des micros à sortie faible ou moyenne ; avec des micros puissants, baissez la sensibilité (RATE en Env R et Env P, DEPTH en Env D)."],
 mode_cap="Le sélecteur MODE (Sine, puis Env P) : il tourne cran par cran jusqu'à sa nouvelle position et l'étiquette du mode choisi s'allume en bleu.",
 fs_t="6. Footswitch, LED et synchro tempo",
 fs=["<b>Flexi-Switch</b> (comme sur l'Aqueduct) : un clic bref met l'effet en marche ou le coupe. Si l'effet est coupé et que vous maintenez l'appui, le footswitch devient momentané : l'effet agit tant que vous appuyez et se coupe au relâchement (au-delà d'environ 0,45 s). Le bouton s'assombrit tant qu'il est enfoncé. Ce comportement se désactive par clic droit &gt; <b>Settings</b> &gt; <b>Flexi-Switch: hold = momentary</b>.",
     "Le bypass et les commutations passent par un court fondu de 12 ms (aucun clic), comme la commutation silencieuse à relais de la pédale. La <b>LED</b> s'allume et s'éteint en fondu et éclaire la façade autour d'elle.",
     "<b>Synchro tempo</b> (clic droit &gt; <b>Tempo sync</b>) : le LFO suit le tempo du DAW et RATE choisit la valeur de note d'un cycle : " + DIVS.replace("bars", "mesures").replace("bar", "mesure") + " (D = pointée, T = triolet). Quand le transport est en lecture, la phase du LFO est calée sur les mesures. La synchro s'applique à Sine, Triangle, Ramp, Square, Random et Env D. Sans tempo de l'hôte, l'écran affiche NO TEMPO et RATE fonctionne normalement.",
     "Tous les paramètres sont automatisables dans le DAW (Rate, Depth, Mode, Tempo Sync, Footswitch, Flexi-Switch, mode du footswitch MIDI)."],
 fs_cap="Footswitch : bypass (LED éteinte), effet en marche, enfoncé (bouton assombri).",
 midi_t="7. MIDI",
 midi_txt=["<b>MIDI Learn sur toutes les commandes</b> : clic droit sur RATE, DEPTH, MODE ou le footswitch. Le haut du menu affiche <b>MIDI Learn: &lt;Nom&gt; (CC n / none)</b> avec l'assignation actuelle, <b>Clear MIDI: &lt;Nom&gt;</b> et, tant qu'un apprentissage est en attente, <b>Cancel MIDI learn</b>. Bougez ensuite une pédale, un bouton ou appuyez sur un footswitch de votre contrôleur : l'écran affiche <b>MIDI LEARN: move a control for &lt;Nom&gt;</b>, puis <b>&lt;Nom&gt; = CC n</b> pendant 2 secondes.",
           "Chaque menu clic droit contient aussi le sous-menu <b>MIDI map</b> : <b>Learn</b> pour chacune des 5 commandes (Tempo Sync compris), <b>Cancel MIDI learn</b> et <b>Reset MIDI to defaults (CC 20-24)</b>. Un numéro de CC ne pilote qu'une seule commande. L'apprentissage accepte les CC 0 à 119 ; Pipeline écoute tous les canaux. <b>Les assignations sont sauvegardées avec le projet.</b>"],
 midi_hdr=["Commande", "CC par défaut", "Type"],
 midi=[["Rate", "CC 20", "Continu 0-127 ; 14 bits avec CC 52"], ["Depth", "CC 21", "Continu 0-127 ; 14 bits avec CC 53"],
       ["Mode", "CC 22", "Sélecteur 8 positions : 0-127 découpé en 8 zones égales (Sine à Env P)"],
       ["Tempo Sync", "CC 23", "Bascule : 64 et plus = ON"],
       ["Footswitch", "CC 24", "Chaque appui bascule marche / arrêt (par défaut, pour les footswitchs momentanés comme la M-Vave Chocolate) ou à accrochage (127 = on / 0 = off)"]],
 midi2=["<b>Mode du footswitch MIDI</b> : clic droit &gt; <b>Settings</b> &gt; <b>MIDI footswitch: each press toggles on / off</b> (par défaut : un appui = marche, l'appui suivant = arrêt, inutile de maintenir) ou <b>MIDI footswitch latching (127 = on / 0 = off)</b> pour les footswitchs à accrochage.",
        "<b>Pédales d'expression</b> sur RATE ou DEPTH : mouvement lissé (rampe entre deux messages, puis lissage à 2 pôles), CC 14 bits accepté, course apprise automatiquement (0 et 100 % atteints même si la pédale n'envoie que 2-116) et petites zones mortes aux butées. Une pédale sur RATE en Env P règle l'amplitude du bend en temps réel.",
        "<b>Program Change</b> 1 à 15 : presets d'usine."],
 win_t="8. Fenêtre et écran",
 win=["Clic droit &gt; <b>Window size</b> : <b>60 % (default)</b>, <b>75 %</b>, <b>100 %</b>. La fenêtre s'ouvre à la même taille par défaut que les autres pédales simples Studio Wiga et ne peut jamais être réduite en dessous ; tirez le coin pour l'agrandir (proportions bloquées).",
      "La partie gauche de l'écran affiche pendant 2,5 s la valeur de la commande que vous venez de bouger, avec son rôle dans le mode en cours (par exemple <b>RATE (BEND RANGE)</b> en Env P, <b>DEPTH (MIX) 50 / 50</b>). Le reste du temps, elle montre le mode, la vitesse du LFO et l'écart de hauteur en cents en direct (la profondeur du bend en Env P).", "<b>Oscilloscope</b> : la partie droite de l'écran dessine la modulation de hauteur en direct (animée, 30 images par seconde), en défilant de droite à gauche : le bord droit, c'est ce que vous entendez maintenant. RATE change le nombre de cycles, DEPTH la hauteur, MODE la forme (sinus, triangle, rampe sonar, carré, aléatoire). Dans les modes d'enveloppe, la courbe suit votre jeu : la vague gonfle (Env D), accélère (Env R) ou plonge comme un levier de vibrato (Env P) à chaque attaque, et reste plate quand rien ne joue. En bypass, la courbe devient plate et grisée."],
 disp_cap="Écran : informations et oscilloscope en direct (Sine, Env P), puis valeur de la commande qu'on règle (Rate en Hz, Rate en synchro tempo).",
 pre_t="9. Presets",
 pre=["15 presets d'usine sont fournis (aussi dans le menu de presets du DAW et en Program Change MIDI). Les deux premiers sont les « Suggested Settings » du manuel d'origine. Neuf emplacements utilisateur peuvent être enregistrés depuis le menu des presets (ils gardent Rate, Depth, Mode et Tempo Sync)."],
 fac_hdr=["N°", "Preset", "Mode", "Rate", "Depth", "Description"],
 tips_t="10. Conseils d'utilisation",
 tips=["Dans Reaper, placez Pipeline en premier, avant Two Notes Genome ou tout simulateur d'ampli : les modes d'enveloppe ont besoin du signal clair et dynamique de la guitare, et un vibrato devant l'ampli sonne comme la pédale sur un pedalboard.",
       "Env P avec le Flexi-Switch : maintenez le footswitch seulement sur les accords à « tordre », pour le jeu en glissé façon Kevin Shields.",
       "Accordages graves : Pipeline n'a pas de détection de hauteur, une 7 cordes en G ou plus bas fonctionne sans limite. Sur les notes graves, gardez DEPTH un peu plus bas : un même écart en cents s'entend davantage en battements sur un gros accord grave.",
       "Une pédale d'expression sur DEPTH en Sine ou Triangle fait entrer le vibrato en fin de note tenue ; sur RATE, elle accélère une ondulation façon Leslie.",
       "Square à RATE élevé et DEPTH faible donne une texture rapide qui papillonne ; Random à DEPTH minimum ajoute un léger pleurage de bande aux arpèges clairs."],
 tech_t="11. Caractéristiques techniques",
 tech=[["Format", "VST3, Windows (x64) et macOS (Apple Silicon + Intel)"], ["Canaux", "Mono ou stéréo (même modulation sur les deux canaux)"],
       ["Moteur", "Ligne de retard modulée avec interpolation Hermite 4 points, tables de LFO dessinées en hauteur, suiveur d'enveloppe (attaque 1,5 ms, relâchement 140 ms), passe-bas 2 pôles à 7,2 kHz et saturation douce sur la voie traitée, fondu entre têtes de lecture aux changements de mode et de preset"],
       ["Retard", "0,6 ms minimum plus la moitié de la course de modulation (jusqu'à environ 11 ms à DEPTH maximum et RATE lent) ; aucune latence déclarée à l'hôte, comme un vibrato matériel (l'original mesurait environ 52 ms)"],
       ["Plage de hauteur", "Jusqu'à environ +4 / -6 demi-tons (limiteur de pente : jamais de lecture à l'envers)"],
       ["Fréquences", "44,1 à 192 kHz"], ["Version", VERSION],
       ["Fenêtre", "60 % (par défaut, c'est aussi la taille minimale), 75 %, 100 % ; anti-gel v2 sous Windows (rendu logiciel, caches d'affichage refaits par un timer, chien de garde de redessin, aucun appel à l'hôte depuis le thread audio)"],
       ["MIDI", "MIDI Learn sur 5 commandes (sauvegardé avec le projet), CC 20 à 24 par défaut (14 bits sur CC 52-53), Program Change 1 à 15, tous canaux"]],
)

W = A4[0] - 36 * mm
def section(lang):
    t = T[lang]; f = []
    f.append(NextPageTemplate("p"))
    f.append(Spacer(1, 2 * mm))
    f.append(P(t["lang"], "coverlang"))
    f.append(Spacer(1, 2 * mm))
    f.append(img(cover, W * 0.56))
    f.append(Spacer(1, 2 * mm))
    f.append(P("P I P E L I N E", "cover"))
    f.append(P(t["sub"], "coversub"))
    f.append(Spacer(1, 2 * mm))
    f.append(P(t["ver"], "coversub"))
    f.append(Spacer(1, 6 * mm))
    f.append(img(os.path.join(ROOT, "assets", "logo_studio_wiga_blanc.png"), 52 * mm))
    f.append(PageBreak())
    f.append(P(t["intro_t"], "h1")); f += [P(x) for x in t["intro"]]
    f.append(P(t["inst_t"], "h1"))
    for h, x in t["inst"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(PageBreak())
    f.append(P(t["ov_t"], "h1"))
    ov = Table([[img(annotated, 92 * mm), table(t["ov_rows"], [11 * mm, 25 * mm, W - 96 * mm - 36 * mm])]], colWidths=[96 * mm, W - 96 * mm])
    ov.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    f.append(ov)
    f.append(PageBreak())
    f.append(P(t["ctl_t"], "h1"))
    for h, x in t["ctl"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(KeepTogether([Spacer(1, 3 * mm), img(knobs_img, W * 0.55), P(t["knobs_cap"], "small")]))
    f.append(CondPageBreak(120 * mm))
    f.append(P(t["modes_t"], "h1")); f.append(P(t["modes_intro"]))
    f.append(table(t["modes"], [20 * mm, W - 20 * mm - 64 * mm, 32 * mm, 32 * mm]))
    f.append(Spacer(1, 3 * mm))
    f += bullets(t["envp"])
    f.append(KeepTogether([Spacer(1, 2 * mm), img(mode_img, W * 0.50), P(t["mode_cap"], "small")]))
    f.append(P(t["fs_t"], "h1")); f += bullets(t["fs"])
    f.append(KeepTogether([Spacer(1, 2 * mm), img(fs_img, W * 0.50), P(t["fs_cap"], "small")]))
    f.append(P(t["midi_t"], "h1")); f += [P(x) for x in t["midi_txt"]]
    f.append(Spacer(1, 2 * mm)); f.append(KeepTogether([table([t["midi_hdr"]] + t["midi"], [30 * mm, 24 * mm, W - 54 * mm])])); f.append(Spacer(1, 3 * mm))
    f += bullets(t["midi2"])
    f.append(P(t["win_t"], "h1")); f += [P(x) for x in t["win"]]
    f.append(KeepTogether([img(disp_img, W * 0.92), Spacer(1, 2 * mm), img(disp2_img, W * 0.92), P(t["disp_cap"], "small")]))
    f.append(CondPageBreak(235 * mm))
    f.append(P(t["pre_t"], "h1")); f += [P(x) for x in t["pre"]]
    rows = [t["fac_hdr"]]
    for i, (n, r, d, m) in enumerate(FACTORY):
        rows.append([str(i + 1), "<b>" + n + "</b>", MODES[m], rate_s(r, m, lang), depth_s(d, m, lang), FACT_DESC[lang][i]])
    f.append(table(rows, [8 * mm, 32 * mm, 18 * mm, 22 * mm, 20 * mm, W - 100 * mm]))
    f.append(PageBreak())
    f.append(P(t["tips_t"], "h1")); f += bullets(t["tips"])
    f.append(KeepTogether([P(t["tech_t"], "h1"), table(t["tech"], [32 * mm, W - 32 * mm], header=False)]))
    f.append(PageBreak())
    return f

def deco(c, doc):
    c.saveState()
    c.setFillColor(DARK); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 6.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
    c.setFont("Pop", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Pipeline (Studio Wiga) · v" + VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="Pipeline - Manual / Notice v" + VERSION, author="Studio Wiga")
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 3 * mm, A4[0], 3 * mm, stroke=0, fill=1); c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
en = section("en"); fr = section("fr")
en[-1:] = [NextPageTemplate("cover"), PageBreak()]
story = en + fr[:-1]
doc.build(story)
print(OUT)
