"""
PIPELINE (Studio Wiga) - fond du plugin a partir du visuel de l'utilisateur (design/source/pipeline_visuel.jpg, 812 x 1024).

Le visuel est la reference : son eclairage (lumiere douce en haut a gauche) est conserve.
Modifications demandees (v1.1.0) :
  - pedale un peu moins haute : une bande de 30 px est retiree entre l'ecran et le footswitch,
  - potards RATE / DEPTH abaisses (+18 px), bloc MODE abaisse (+12 px) et inscription MODE placee AU-DESSUS du selecteur,
  - LED deplacee en haut (au centre, entre les deux potards),
  - footswitch et logo Studio Wiga remontes (le logo ne touche plus le filet du cadre).
Etapes :
  1. reperes des potards effaces (ils sont redessines et tournent dans le plugin), textes de l'ecran effaces (le plugin y ecrit),
  2. plaque nue : chaque element est retire (interpolation par ligne de la facade + grain de la photo),
  3. bande retiree, elements recolles a leur nouvelle place par transfert de difference (ombres et reflets compris),
  4. recadrage aux proportions 760 x 958 puis mise a l'echelle 1520 x 1916,
  5. footswitch d'ECHOFLEX (photo detouree, ombres comprises), LED (bague chromee, lentille eteinte) + calque d'eclairage,
  6. Layout.h, tools/layout.json, tools/pedal_mask.png.

Usage : python3 tools/make_background.py
"""
import os, json, math
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'design', 'source', 'pipeline_visuel.jpg')
rng = np.random.default_rng(7)

A = cv2.cvtColor(cv2.imread(SRC), cv2.COLOR_BGR2RGB).astype(np.float32)
H, W = A.shape[:2]
lum = lambda a: a.mean(-1)

# ------------------------------------------------------------------ reperes mesures sur le visuel (px)
RATE_C, DEPTH_C, MODE_C = (277.5, 211.0), (533.4, 211.0), (405.8, 422.9)
CAP_R, SKIRT_R = 36.0, 53.0
MODE_CAP_R, MODE_SKIRT_R = 26.5, 38.0
FOOT_C = (406.0, 895.0)
DISPLAY = (207, 656, 605, 772)
ROW = (222.0, 674.0, 590.0, 712.0)        # ligne d'etat (texte bleu)
BAR = (225.0, 727.3, 588.3, 760.0)        # barre de presets (cadre garde)
BORDER_Y = 965                            # filet bas du cadre

# deplacements (px du visuel)
D_KNOBS, D_MODE = 18, 12
CUT0, CUT1 = 790, 820                     # bande retiree (entre l'ecran et le footswitch)
CUT = CUT1 - CUT0
MODE_WORD_NEW_Y = 340.0                   # centre de l'inscription MODE (coordonnees finales)
LOGO_DY = -38                             # logo : remonte de 8 px de plus que la coupe
FOOT_NEW = (406.0, 851.0)                 # footswitch (coordonnees finales)
LED_NEW = (406.0, 118.0)                  # LED en haut, entre les potards
FS_HEX_W = 92.0                           # largeur de l'ecrou du footswitch (px du visuel)

# ------------------------------------------------------------------ 1. reperes des potards et textes de l'ecran
def erase_pointer(c, r):
    """ efface le repere clair du chapeau : inpainting limite au chapeau (l'exterieur est noirci pour ne pas couler) """
    global A
    cx, cy = c
    YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
    inside = np.hypot(XX - cx, YY - cy) <= r - 1.0
    m = ((lum(A) > 95) & inside).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) * inside
    tmp = A.copy()
    tmp[~inside] = np.median(A[inside & (lum(A) < 70)], 0)
    out = cv2.inpaint(np.clip(tmp, 0, 255).astype(np.uint8), m.astype(np.uint8), 4, cv2.INPAINT_TELEA).astype(np.float32)
    out = cv2.GaussianBlur(out, (0, 0), 0.6)
    A = np.where(m[..., None] > 0, out + rng.normal(0, 1.2, out.shape).astype(np.float32), A)

erase_pointer(RATE_C, CAP_R)
erase_pointer(DEPTH_C, CAP_R)
erase_pointer(MODE_C, MODE_CAP_R)

def erase_display_text(box, thr=55):
    """ texte de l'ecran : remplace par la trame de l'ecran prise sur la meme ligne (decalage pair = trame de 2 px) """
    global A
    x0, y0, x1, y1 = box
    reg = A[y0:y1, x0:x1]
    m = cv2.dilate((lum(reg) > thr).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    out = reg.copy(); todo = m.copy()
    for d in sorted(range(-220, 222, 2), key=abs):
        if d == 0 or not todo.any(): continue
        ys, xs = np.where(todo)
        sx = xs + x0 + d
        ok = (sx >= DISPLAY[0] + 14) & (sx <= DISPLAY[2] - 14)
        sxc = np.clip(sx - x0, 0, x1 - x0 - 1)
        inbox = (sx >= x0) & (sx < x1)
        src_bad = np.zeros_like(ok); src_bad[inbox] = m[ys[inbox], sxc[inbox]]
        good = ok & ~src_bad & ~(lum(A[ys + y0, np.clip(sx, 0, W - 1)]) > thr)
        out[ys[good], xs[good]] = A[ys[good] + y0, sx[good]]
        todo[ys[good], xs[good]] = False
    A[y0:y1, x0:x1] = out

erase_display_text((296, 676, 516, 711))      # ligne d'etat
erase_display_text((318, 731, 510, 758))      # nom du preset
erase_display_text((231, 735, 253, 752))      # fleches
erase_display_text((560, 735, 582, 752))

# ------------------------------------------------------------------ 2. plaque nue
def grain(shape, std=2.35):
    g = rng.normal(0, 1, shape[:2]).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.7); g *= std / (g.std() + 1e-6)
    return g[..., None] * np.ones(3, np.float32)

def row_fill(img, box, edge=4):
    """ facade sous l'element : interpolation lineaire par ligne entre les bords du cadre, lissee verticalement """
    x0, y0, x1, y1 = box
    left = np.median(img[y0:y1, x0:x0 + edge], axis=1)
    right = np.median(img[y0:y1, x1 - edge:x1], axis=1)
    t = np.linspace(0, 1, x1 - x0, dtype=np.float32)[None, :, None]
    f = left[:, None, :] * (1 - t) + right[:, None, :] * t
    return cv2.GaussianBlur(f, (0, 0), sigmaX=0.1, sigmaY=2.0)

BOXES = {
    'rate':  (200, 108, 374, 316), 'depth': (450, 108, 630, 316),
    'mode':  (296, 336, 516, 503), 'word':  (374, 503, 438, 528),
    'led':   (360, 775, 452, 848), 'foot':  (338, 824, 476, 951), 'logo': (326, 940, 488, 964),
}
FILL = {}                     # facade lisse (sans grain) sous chaque element
ALPHA = {}                    # masque doux de l'element (ombres comprises)
plate = A.copy()
for k in ('rate', 'depth', 'mode', 'word', 'led', 'foot', 'logo'):
    x0, y0, x1, y1 = BOXES[k]
    f = row_fill(plate, BOXES[k])
    dev = np.abs(A[y0:y1, x0:x1] - f).max(-1)
    a = np.clip((dev - 4.0) / 12.0, 0, 1)
    a = cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.4)
    if k == 'logo':           # logo : seulement les lettres (le filet du cadre, juste dessous, ne bouge pas)
        lg = (lum(A[y0:y1, x0:x1]) > 100).astype(np.float32)
        lg[BORDER_Y - 2 - y0:] = 0
        a = cv2.GaussianBlur(cv2.dilate(lg, np.ones((3, 3), np.uint8)), (0, 0), 0.8)
    # bord du cadre : fondu de 4 px (aucune arete de rectangle) ; logo : fondu lateral seulement
    fe = np.ones_like(a); e = 4
    for i in range(e):
        w = (i + 0.5) / e
        fe[:, i] *= w; fe[:, -1 - i] *= w
        if k != 'logo': fe[i, :] *= w; fe[-1 - i, :] *= w
    FILL[k] = f; ALPHA[k] = a
    region = f + grain(f.shape)
    wbox = np.clip(fe * 1.0, 0, 1)[..., None]
    blended = plate[y0:y1, x0:x1] * (1 - wbox) + region * wbox
    plate[y0:y1, x0:x1] = blended

# filet du cadre sous le logo : le bas des lettres (et des anneaux) le touchait -> filet refait a partir d'une zone propre
fx0, fx1 = 328, 486
prof_l = np.median(A[BORDER_Y - 5:BORDER_Y + 4, 306:322], axis=1)
prof_r = np.median(A[BORDER_Y - 5:BORDER_Y + 4, 492:508], axis=1)
t = np.linspace(0, 1, fx1 - fx0, dtype=np.float32)[None, :, None]
line = prof_l[:, None, :] * (1 - t) + prof_r[:, None, :] * t + grain((9, fx1 - fx0, 3), 1.5)
plate[BORDER_Y - 5:BORDER_Y + 4, fx0:fx1] = line

# ------------------------------------------------------------------ 3. coupe + elements a leur nouvelle place
XF = 8
top, bot = plate[:CUT0], plate[CUT1:]
ramp = np.linspace(0, 1, XF, dtype=np.float32)[:, None, None]
seam = plate[CUT0 - XF:CUT0] * (1 - ramp) + plate[CUT1 - XF:CUT1] * ramp
P2 = np.concatenate([plate[:CUT0 - XF], seam, bot], axis=0)
H2 = P2.shape[0]

def paste_delta(k, dx, dy):
    """ recolle un element : nouvelle facade + alpha x (photo - facade d'origine) -> ombres et reflets suivent """
    global P2
    x0, y0, x1, y1 = BOXES[k]
    delta = (A[y0:y1, x0:x1] - FILL[k]) * ALPHA[k][..., None]
    nx0, ny0 = x0 + dx, y0 + dy
    P2[ny0:ny0 + (y1 - y0), nx0:nx0 + (x1 - x0)] += delta

paste_delta('rate', 0, D_KNOBS)
paste_delta('depth', 0, D_KNOBS)
paste_delta('mode', 0, D_MODE)
paste_delta('word', 0, int(round(MODE_WORD_NEW_Y - (BOXES['word'][1] + BOXES['word'][3]) / 2)))
paste_delta('logo', 0, LOGO_DY)

# ------------------------------------------------------------------ 4. recadrage 760 x 958 et mise a l'echelle 1520 x 1916
WC = int(round(H2 * 760 / 958))
CX0 = (W - WC) // 2
P3 = P2[:, CX0:CX0 + WC]
W2F, H2F = 1520, 1916
canvas = cv2.resize(np.clip(P3, 0, 255), (W2F, H2F), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
SX, SY = W2F / WC, H2F / H2
def T(p): return ((p[0] - CX0) * SX, p[1] * SY)          # px du visuel (apres coupe) -> px du fond 2x
def U(p): x, y = T(p); return (x / 2.0, y / 2.0)          # -> unites 760 x 958

# ------------------------------------------------------------------ 5a. footswitch d'ECHOFLEX
fs = Image.open(os.path.join(HERE, 'fs_echoflex.png')).convert('RGBA')
sc = FS_HEX_W * SX / 247.0                                # 247 px = largeur de l'ecrou dans le sprite
fs = fs.resize((round(fs.width * sc), round(fs.height * sc)), Image.LANCZOS)
fa = np.asarray(fs).astype(np.float32) / 255
fcx, fcy = T(FOOT_NEW)
# centre de l'ecrou dans le sprite : (199.5, 198) px -> recale le sprite sur le centre voulu
ox, oy = int(round(fcx - 199.5 * sc)), int(round(fcy - 198.0 * sc))
h_, w_ = fa.shape[:2]
reg = canvas[oy:oy + h_, ox:ox + w_]
canvas[oy:oy + h_, ox:ox + w_] = reg * (1 - fa[..., 3:]) + fa[..., :3] * 255 * fa[..., 3:]

# ------------------------------------------------------------------ 5b. LED eteinte : bague chromee, gorge sombre, lentille bleue sombre
YY, XX = np.mgrid[0:H2F, 0:W2F].astype(np.float32)
lx, ly = T(LED_NEW)
d = np.hypot(XX - lx, YY - ly)
RING, LENS = 19.0, 12.6                                   # px du fond 2x
# ombre portee de la bague (lumiere en haut a gauche)
sh = cv2.GaussianBlur((np.hypot(XX - lx - 3, YY - ly - 4) < RING).astype(np.float32), (0, 0), 3.5)
canvas *= (1 - 0.45 * sh * (d >= RING - 1))[..., None]
ang = np.arctan2(YY - ly, XX - lx)
ringLight = 0.5 + 0.5 * np.cos(ang - math.atan2(-0.62, -0.46))
ring = np.clip(RING - d + 0.5, 0, 1) * np.clip(d - LENS + 0.5, 0, 1)
bevel = np.clip((d - LENS) / (RING - LENS), 0, 1)
ringCol = (55 + 175 * ringLight ** 1.6 * (0.55 + 0.45 * np.sin(bevel * math.pi)))[..., None] * np.array([0.98, 1.0, 1.03])
canvas = canvas * (1 - ring[..., None]) + ringCol * ring[..., None]
groove = np.exp(-((d - LENS) / 1.1) ** 2)
canvas *= (1 - 0.6 * groove)[..., None]
lens = np.clip(LENS - d + 0.5, 0, 1)
LED_COL = np.array([0.22, 0.62, 1.00], np.float32)                           # bleu de la LED du visuel
lensOff = np.array([8, 20, 38], np.float32) * (0.55 + 0.45 * np.clip(1 - d / LENS, 0, 1))[..., None]
dome = np.exp(-(((XX - lx + LENS * 0.33) / (LENS * 0.26)) ** 2 + ((YY - ly + LENS * 0.38) / (LENS * 0.20)) ** 2)) * 125
lensOff = lensOff + dome[..., None]
canvas = canvas * (1 - lens[..., None]) + lensOff * lens[..., None]

out = np.clip(canvas, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(ROOT, 'background.jpg'), quality=93, subsampling=0)

# ------------------------------------------------------------------ 5c. calque d'eclairage de la LED (la facade recoit la lumiere)
RAD = 220
x0, y0 = int(round(lx - RAD)), int(round(ly - RAD))
sub = canvas[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD].copy()
gy2, gx2 = np.mgrid[0:2 * RAD, 0:2 * RAD].astype(np.float32)
dd = np.hypot(gx2 + x0 - lx, gy2 + y0 - ly)
def lamb(h): return (h * h / (h * h + dd * dd)) ** 1.5
I = 1.30 * lamb(16) + 0.30 * lamb(70) + 0.09 * lamb(170)
halo = 0.10 * lamb(26)
litL = sub * (1 + I[..., None] * LED_COL * 2.4) + halo[..., None] * LED_COL * 255
core = np.clip(1 - dd / LENS, 0, 1)
lensOn = (LED_COL * 255)[None, None, :] * (0.55 + 0.45 * core[..., None]) + (np.clip(core * 1.8 - 0.9, 0, 1) ** 1.5 * 255)[..., None] * (1 - LED_COL * 0.3)
lensOn += (dome[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD] * 0.6)[..., None]
lm = np.clip(LENS - dd + 0.5, 0, 1)[..., None]
litL = litL * (1 - lm) + lensOn * lm
edge = np.clip((RAD - dd) / (RAD * 0.35), 0, 1) ** 2
a = np.clip((I + halo * 3.0) * 2.2, 0, 1) * edge
a = np.maximum(a, lm[..., 0])
rgba = np.dstack([np.clip(litL, 0, 255), a * 255]).astype(np.uint8)
Image.fromarray(rgba, 'RGBA').save(os.path.join(ROOT, 'glow_led.png'), optimize=True)

# ------------------------------------------------------------------ 6a. silhouette (boitier + jacks) pour la notice
f8 = out.astype(np.int16)
blue = ((f8[..., 2] - f8[..., 0]) > 22).astype(np.uint8)
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
cnts, _ = cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
SIL = np.zeros((H2F, W2F), np.uint8)
cv2.drawContours(SIL, [max(cnts, key=cv2.contourArea)], -1, 255, -1)
wall = cv2.GaussianBlur(out.astype(np.float32).mean(-1), (0, 0), 25)
jk = (np.abs(out.astype(np.float32).mean(-1) - wall) > 14).astype(np.uint8) * 255
for (jx0, jx1) in ((int(T((118, 0))[0]), int(T((170, 0))[0])), (int(T((640, 0))[0]), int(T((700, 0))[0]))):
    jy0, jy1 = int(T((0, 272))[1]), int(T((0, 362))[1])
    SIL[jy0:jy1, jx0:jx1] = np.maximum(SIL[jy0:jy1, jx0:jx1], jk[jy0:jy1, jx0:jx1])
SIL = cv2.GaussianBlur(cv2.morphologyEx(SIL, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)), (0, 0), 0.8)
Image.fromarray(SIL).save(os.path.join(HERE, 'pedal_mask.png'))

# ------------------------------------------------------------------ 6b. reperes pour le code (unites 760 x 958)
k = 958.0 / H2
rate, depth = U((RATE_C[0], RATE_C[1] + D_KNOBS)), U((DEPTH_C[0], DEPTH_C[1] + D_KNOBS))
mode = U((MODE_C[0], MODE_C[1] + D_MODE))
led, foot = U(LED_NEW), U(FOOT_NEW)
def R(b): p0, p1 = U((b[0], b[1])), U((b[2], b[3])); return [round(p0[0], 2), round(p0[1], 2), round(p1[0] - p0[0], 2), round(p1[1] - p0[1], 2)]
info = {
    'rate': rate, 'depth': depth, 'mode': mode, 'knobTop': CAP_R * k, 'knobSkirt': SKIRT_R * k,
    'modeTop': MODE_CAP_R * k, 'modeSkirt': MODE_SKIRT_R * k, 'led': led, 'foot': foot, 'footR': FS_HEX_W * 0.5 * k * 0.92,
    'ledLensR': LENS / 2, 'glowRect': [x0 / 2, y0 / 2, RAD, RAD], 'row': R(ROW), 'bar': R(BAR),
    'display': R(DISPLAY), 'cropX0': CX0, 'cut': [CUT0, CUT1],
}
json.dump(info, open(os.path.join(HERE, 'layout.json'), 'w'), indent=1)

def P(p): return '{ %.2ff, %.2ff }' % (p[0], p[1])
def Rr(r): return '{ %.2ff, %.2ff, %.2ff, %.2ff }' % tuple(r)
with open(os.path.join(ROOT, 'Layout.h'), 'w') as fo:
    fo.write('// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)\n#pragma once\n')
    fo.write('#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{\n')
    fo.write('    const juce::Point<float> ratePos %s, depthPos %s, modePos %s;\n' % (P(rate), P(depth), P(mode)))
    fo.write('    const float knobTop = %.2ff, knobSkirt = %.2ff, modeTop = %.2ff, modeSkirt = %.2ff;\n'
             % (info['knobTop'], info['knobSkirt'], info['modeTop'], info['modeSkirt']))
    fo.write('    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions\n')
    fo.write('    const juce::Point<float> ledPos %s, footPos %s;\n' % (P(led), P(foot)))
    fo.write('    const float footR = %.2ff, ledLensR = %.2ff;\n' % (info['footR'], info['ledLensR']))
    fo.write('    const juce::Rectangle<float> glowRect { %.2ff, %.2ff, %.2ff, %.2ff };\n' % tuple(info['glowRect']))
    fo.write('    const juce::Rectangle<float> rowRect %s;\n' % Rr(info['row']))
    fo.write('    const juce::Rectangle<float> barRect %s;\n' % Rr(info['bar']))
    fo.write('}\n')
print('ok', WC, H2, CX0)
