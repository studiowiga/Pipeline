"""
PIPELINE (Studio Wiga) - fond du plugin a partir du visuel « vagues » de l'utilisateur
(design/source/pipeline_visuel_vagues.png, 1117 x 1408).

Le visuel est la reference : son eclairage (lumiere douce en haut a gauche) et ses vagues sont conserves.
Modifications demandees :
  - pedale un peu moins haute : la zone entre l'ecran et le footswitch (ou etait la LED) est resserree,
  - potards RATE / DEPTH abaisses (+14 px), inscription MODE placee AU-DESSUS du selecteur,
  - LED deplacee en haut (au centre, entre les deux potards),
  - footswitch et logo Studio Wiga remontes (le logo ne touche plus le footswitch ni le filet du cadre),
  - pedale agrandie dans la fenetre (marges du mur reduites au minimum, taille de fenetre inchangee).
Les vagues passant sous les elements du bas, le footswitch reste celui du visuel (deplace d'un bloc, sans retouche).
Etapes :
  1. reperes des potards et textes de l'ecran effaces (le plugin les redessine),
  2. potards, MODE et LED retires de la facade unie (interpolation par ligne + grain), logo efface sur les vagues,
  3. potards et MODE recolles a leur nouvelle place par transfert de difference (ombres comprises),
  4. bas de la pedale remappe ligne par ligne : bande de la LED resserree, bloc du footswitch deplace sans deformation,
  5. logo recolle (matte blanc), recadrage serre aux proportions 760 x 958, mise a l'echelle 1520 x 1916,
  6. LED (bague chromee, lentille eteinte) + calque d'eclairage, Layout.h, tools/layout.json, tools/pedal_mask.png.

Usage : python3 tools/make_background.py
"""
import os, json, math
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'design', 'source', 'pipeline_visuel_vagues.png')
rng = np.random.default_rng(7)

A = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32)
H, W = A.shape[:2]
lum = lambda a: a.mean(-1)

# ------------------------------------------------------------------ reperes mesures sur le visuel (px)
RATE_C, DEPTH_C, MODE_C = (383.0, 292.0), (735.0, 292.0), (559.0, 583.0)
CAP_R, SKIRT_R = 54.0, 72.0
MODE_CAP_R, MODE_SKIRT_R = 35.0, 50.0
FOOT_CAP = (558.5, 1237.0)               # centre du bouton du footswitch (dessus)
FOOT_NUT_R = 74.0
DISPLAY = (287, 903, 833, 1060)
ROW = (300.0, 922.0, 820.0, 990.0)       # ligne d'etat (texte bleu)
BAR = (308.0, 998.0, 808.0, 1046.0)      # barre de presets (cadre garde)
LOGO_BOX = (455, 1302, 664, 1325)

D_KNOBS = 26                              # potards (et leurs graduations / etiquettes) abaisses
MODE_WORD_NEW_Y = 449.0
LED_NEW = (558.0, 124.0)
# remappage du bas (destination <- source) : identite jusqu'a l'ecran, bande de la LED resserree,
# bloc du footswitch rigide, bande sous le footswitch un peu etiree (place du logo), puis tout remonte de 20 px
KNOTS = [(0, 0), (1062, 1062), (1118, 1144), (1280, 1306), (1306, 1326)]
SHIFT = 20
LOGO_DST_BOTTOM = 1300                   # bas du logo (bas des anneaux) dans l'image remappee

# ------------------------------------------------------------------ 1. reperes des potards et textes de l'ecran
def erase_pointer(c, r):
    global A
    cx, cy = c
    YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
    inside = np.hypot(XX - cx, YY - cy) <= r - 1.0
    m = ((lum(A) > 95) & inside).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) * inside
    tmp = A.copy()
    tmp[~inside] = np.median(A[inside & (lum(A) < 70)], 0)
    out = cv2.inpaint(np.clip(tmp, 0, 255).astype(np.uint8), m.astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32)
    out = cv2.GaussianBlur(out, (0, 0), 0.7)
    A = np.where(m[..., None] > 0, out + rng.normal(0, 1.2, out.shape).astype(np.float32), A)

# (les potards du visuel sont retires en entier : le plugin dessine les potards moletes de Holyverb)

def erase_display_text(box, thr=36):
    """ texte de l'ecran : remplace par la trame de l'ecran prise sur la meme ligne (decalages pairs) """
    global A
    x0, y0, x1, y1 = box
    reg = A[y0:y1, x0:x1]
    m = cv2.dilate((lum(reg) > thr).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    out = reg.copy(); todo = m.copy()
    for d in sorted(range(-300, 302, 2), key=abs):
        if d == 0 or not todo.any(): continue
        ys, xs = np.where(todo)
        sx = xs + x0 + d
        ok = (sx >= DISPLAY[0] + 26) & (sx <= DISPLAY[2] - 26)
        sxc = np.clip(sx - x0, 0, x1 - x0 - 1)
        inbox = (sx >= x0) & (sx < x1)
        src_bad = np.zeros_like(ok); src_bad[inbox] = m[ys[inbox], sxc[inbox]]
        good = ok & ~src_bad & ~(lum(A[ys + y0, np.clip(sx, 0, W - 1)]) > thr)
        out[ys[good], xs[good]] = A[ys[good] + y0, sx[good]]
        todo[ys[good], xs[good]] = False
    A[y0:y1, x0:x1] = out

erase_display_text((418, 928, 698, 976))       # ligne d'etat
erase_display_text((446, 1006, 670, 1041))     # nom du preset
erase_display_text((318, 1010, 342, 1034))     # fleches
erase_display_text((774, 1010, 798, 1034))

# ------------------------------------------------------------------ 2. facade nue sous les elements de la zone unie
def grain(shape, std=2.3):
    g = rng.normal(0, 1, shape[:2]).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.7); g *= std / (g.std() + 1e-6)
    return g[..., None] * np.ones(3, np.float32)

def robust_edge(strip):
    """ couleur de facade d'une bande de bord, ligne par ligne, sans les bulles ni les traits clairs """
    L = lum(strip)
    ref = np.median(L, axis=1, keepdims=True)
    ok = L <= ref + 12
    out = np.empty((strip.shape[0], 3), np.float32)
    for r in range(strip.shape[0]):
        v = strip[r][ok[r]] if ok[r].any() else strip[r]
        out[r] = np.median(v, axis=0)
    # une ligne entiere prise dans une bulle : on interpole depuis les lignes voisines
    Lr = out.mean(-1); pad = np.pad(Lr, 15, mode='edge'); base = np.array([np.median(pad[i:i + 31]) for i in range(len(Lr))])
    bad = Lr > base + 8
    if bad.any() and (~bad).any():
        for c in range(3): out[bad, c] = np.interp(np.where(bad)[0], np.where(~bad)[0], out[~bad, c])
    return out

def row_fill(img, box, edge=8):
    x0, y0, x1, y1 = box
    left = robust_edge(img[y0:y1, x0:x0 + edge])
    right = robust_edge(img[y0:y1, x1 - edge:x1])
    t = np.linspace(0, 1, x1 - x0, dtype=np.float32)[None, :, None]
    f = left[:, None, :] * (1 - t) + right[:, None, :] * t
    return cv2.GaussianBlur(f, (0, 0), sigmaX=0.1, sigmaY=2.0)

BOXES = {'rate': (276, 150, 524, 428), 'depth': (626, 150, 872, 428), 'modek': (480, 505, 640, 665),
         'word': (516, 690, 602, 726), 'led': (486, 1068, 634, 1146)}
KNOB_OF = {'rate': (RATE_C, SKIRT_R), 'depth': (DEPTH_C, SKIRT_R), 'modek': (MODE_C, MODE_SKIRT_R)}
FILL, ALPHA = {}, {}
plate = A.copy()
for k, (x0, y0, x1, y1) in BOXES.items():
    f = row_fill(plate, BOXES[k])
    dev = np.abs(A[y0:y1, x0:x1] - f).max(-1)
    a = np.clip((dev - 4.0) / 12.0, 0, 1)
    a = cv2.GaussianBlur(cv2.dilate(a, np.ones((5, 5), np.uint8)), (0, 0), 1.4)
    fe = np.ones_like(a); e = 4
    for i in range(e):
        w = (i + 0.5) / e
        fe[i, :] *= w; fe[-1 - i, :] *= w; fe[:, i] *= w; fe[:, -1 - i] *= w
    if k in KNOB_OF:          # potard du visuel retire avec ses reflets et son ombre : seuls les traits clairs
        brighter = np.clip((lum(A[y0:y1, x0:x1]) - lum(f) - 18.0) / 25.0, 0, 1)   # (graduations, etiquettes) restent
        (kcx, kcy), kr = KNOB_OF[k]
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        on_knob = np.hypot(gx - kcx, gy - kcy) < kr + 3.0                          # reflets du potard : retires aussi
        a = a * brighter * (~on_knob)
        # hors de la zone des graduations (bulles, ecume) : les traits clairs restent sur place, ils ne descendent pas
        stay = (gy > kcy + kr + 14.0) | (gx > kcx + kr + 34.0) | (gx < kcx - kr - 34.0)
        plate[y0:y1, x0:x1] += (A[y0:y1, x0:x1] - f) * (a * stay * fe)[..., None]
        a = a * (~stay)
    FILL[k] = f; ALPHA[k] = a * fe
    plate[y0:y1, x0:x1] = plate[y0:y1, x0:x1] * (1 - fe[..., None]) + (f + grain(f.shape)) * fe[..., None]
    if k == 'led':            # les bulles autour de la LED restent : seule la LED et sa lueur disparaissent
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        keep = np.clip((np.hypot(gx - 557.0, gy - 1112.0) - 46.0) / 6.0, 0, 1)
        plate[y0:y1, x0:x1] += (A[y0:y1, x0:x1] - f) * (a * keep)[..., None]

def deshadow(img, c, r, reach=48.0):
    """ ombre portee residuelle d'un potard retire (vers le bas a droite) : la facade est ramenee a sa teinte voisine.
    Gain multiplicatif lisse (basse frequence), calcule sur la facade seule (bulles, ecume et textes exclus). """
    cx, cy = c
    R = int(r + reach + 30)
    x0, y0, x1, y1 = int(cx - R), int(cy - R), int(cx + R), int(cy + R)
    reg = img[y0:y1, x0:x1]
    L = lum(reg)
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.hypot(gx - cx - 6.0, gy - cy - 8.0)
    plain = (L < np.median(L) + 15).astype(np.float32)               # facade (pas les traits clairs)
    low = cv2.GaussianBlur(L * plain, (0, 0), 10) / (cv2.GaussianBlur(plain, (0, 0), 10) + 1e-4)
    ring = (d > r + reach) & (d < r + reach + 26) & (plain > 0)
    ref = np.median(L[ring])
    zone = np.clip((r + reach - d) / 14.0, 0, 1)
    gain = 1 + zone * np.clip(ref / np.maximum(low, 1.0) - 1, 0, 0.9)
    img[y0:y1, x0:x1] = reg * gain[..., None]

for (kc, kr) in KNOB_OF.values():
    deshadow(plate, kc, kr)

# logo sur les vagues : lettres et anneaux effaces (inpainting), matte blanc conserve pour le recoller
lx0, ly0, lx1, ly1 = LOGO_BOX
lreg = plate[ly0 - 6:ly1 + 1, lx0:lx1].copy()
lm = (lum(lreg) > 110).astype(np.uint8)
lm[-2:] = 0                                               # lignes du filet du cadre : pas touchees
lm = cv2.dilate(lm, np.ones((5, 5), np.uint8))
lm[-1:] = 0
bgL = cv2.inpaint(np.clip(lreg, 0, 255).astype(np.uint8), lm, 3, cv2.INPAINT_TELEA).astype(np.float32)
logo_alpha = np.clip((lum(lreg) - lum(bgL)) / np.maximum(235.0 - lum(bgL), 30.0), 0, 1) * (lm > 0)
logo_alpha[-2:] = 0
plate[ly0 - 6:ly1 + 1, lx0:lx1] = np.where(lm[..., None] > 0, bgL + grain(bgL.shape, 1.5), lreg)

def col_fill(img, box, edge=4):
    """ mur et tranche du boitier sous un jack : interpolation verticale (le bord du boitier est vertical) """
    x0, y0, x1, y1 = box
    top = np.median(img[y0:y0 + edge, x0:x1], axis=0); bot = np.median(img[y1 - edge:y1, x0:x1], axis=0)
    t = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    return top[None] * (1 - t) + bot[None] * t

for jb in ((156, 378, 219, 524), (897, 378, 962, 524)):
    x0, y0, x1, y1 = jb
    plate[y0:y1, x0:x1] = col_fill(plate, jb) + grain((y1 - y0, x1 - x0, 3), 1.3)

def paste_delta(img, k, dx, dy):
    x0, y0, x1, y1 = BOXES[k]
    delta = (A[y0:y1, x0:x1] - FILL[k]) * ALPHA[k][..., None]
    img[y0 + dy:y1 + dy, x0 + dx:x1 + dx] += delta

paste_delta(plate, 'modek', 0, 0)
paste_delta(plate, 'rate', 0, D_KNOBS)
paste_delta(plate, 'depth', 0, D_KNOBS)
wb = BOXES['word']
paste_delta(plate, 'word', 0, int(round(MODE_WORD_NEW_Y - (wb[1] + wb[3]) / 2)))

# ------------------------------------------------------------------ 4. remappage du bas, ligne par ligne
Hd = H - SHIFT
kn = KNOTS + [(Hd - 1, Hd - 1 + SHIFT)]
dst = np.array([k[0] for k in kn], np.float32); src = np.array([k[1] for k in kn], np.float32)
yd = np.arange(Hd, dtype=np.float32)
ys = np.interp(yd, dst, src).astype(np.float32)
# raccords adoucis (pas de cassure dans les lignes des vagues), le bloc du footswitch reste rigide
ys_s = cv2.GaussianBlur(ys.reshape(-1, 1), (1, 0), sigmaX=0.1, sigmaY=3.0).ravel()
rigid = (yd >= kn[2][0] + 6) & (yd <= kn[3][0] - 6)
ys = np.where(rigid | (yd < 1056), ys, ys_s)
mapx = np.tile(np.arange(W, dtype=np.float32), (Hd, 1))
mapy = np.repeat(ys[:, None], W, axis=1).astype(np.float32)
P2 = cv2.remap(plate, mapx, mapy, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
def to_dst(y):                                            # ligne source -> ligne destination (pour les reperes)
    return float(np.interp(y, src, dst))

# logo recolle (blanc du visuel) au-dessus du filet
la = logo_alpha
ny0 = LOGO_DST_BOTTOM - la.shape[0] + 1 + 2
reg = P2[ny0:ny0 + la.shape[0], lx0:lx1]
P2[ny0:ny0 + la.shape[0], lx0:lx1] = reg * (1 - la[..., None]) + np.array([236, 238, 236], np.float32) * la[..., None]

# ------------------------------------------------------------------ 4b. pedale un peu plus large : interieur etire de 28 px
# (4,5 %), bords du boitier, filet et coins arrondis deplaces sans deformation
WIDEN = 28
XK_SRC = np.array([0, 248, 868, W - 1], np.float32)
XK_DST = np.array([0, 248, 868 + WIDEN, W - 1 + WIDEN], np.float32)
W2 = W + WIDEN
xd = np.arange(W2, dtype=np.float32)
xs = np.interp(xd, XK_DST, XK_SRC).astype(np.float32)
xs = cv2.GaussianBlur(xs.reshape(1, -1), (0, 1), sigmaX=4.0, sigmaY=0.1).ravel()
P2 = cv2.remap(P2, np.tile(xs[None, :], (P2.shape[0], 1)), np.repeat(np.arange(P2.shape[0], dtype=np.float32)[:, None], W2, axis=1),
               interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
def X(x): return float(np.interp(x, XK_SRC, XK_DST))

# ------------------------------------------------------------------ 5. recadrage serre 760 x 958 et mise a l'echelle 1520 x 1916
CY0 = 31
CY1 = to_dst(1344) + 16
HC = int(round(CY1 - CY0))
WC = int(round(HC * 760 / 958))
CX0 = int(round(X(558.0) - WC / 2))
P3 = P2[CY0:CY0 + HC, CX0:CX0 + WC]
W2F, H2F = 1520, 1916
canvas = cv2.resize(np.clip(P3, 0, 255), (W2F, H2F), interpolation=cv2.INTER_CUBIC).astype(np.float32)
SX, SY = W2F / WC, H2F / HC
def T(p): return ((X(p[0]) - CX0) * SX, (p[1] - CY0) * SY)       # px du visuel (x source, y remappe) -> fond 2x
def U(p): x, y = T(p); return (x / 2.0, y / 2.0)

# ------------------------------------------------------------------ 5b. jacks : embases chromees de Holyverb (OUT a gauche, IN a droite)
def paste_sprite(img, x0, y0):
    global canvas
    a = np.asarray(img).astype(np.float32) / 255
    h_, w_ = a.shape[:2]
    sm = cv2.GaussianBlur(a[..., 3], (0, 0), 4)                       # ombre portee sur le mur (lumiere en haut a gauche)
    canvas[y0 + 5:y0 + 5 + h_, x0 + 4:x0 + 4 + w_] *= (1 - 0.5 * sm)[..., None]
    al = a[..., 3:]
    canvas[y0:y0 + h_, x0:x0 + w_] = canvas[y0:y0 + h_, x0:x0 + w_] * (1 - al) + a[..., :3] * 255 * al
    return a[..., 3]
JACK_Y = T((0, 448.0))[1]
jo = Image.open(os.path.join(ROOT, 'assets', 'kit', 'embase_jack_gauche_OUT.png')).convert('RGBA')
ji = Image.open(os.path.join(ROOT, 'assets', 'kit', 'embase_jack_droite_IN.png')).convert('RGBA')
exL, exR = T((214.0, 0))[0], T((900.5, 0))[0]                     # tranches du boitier
JL = (int(round(exL - jo.width + 4)), int(round(JACK_Y - jo.height / 2)))
JR = (int(round(exR - 4)), int(round(JACK_Y - ji.height / 2)))
aL = paste_sprite(jo, *JL)
aR = paste_sprite(ji, *JR)

# ------------------------------------------------------------------ 6a. LED eteinte : bague chromee, gorge sombre, lentille bleue sombre
YY, XX = np.mgrid[0:H2F, 0:W2F].astype(np.float32)
lx, ly = T(LED_NEW)
d = np.hypot(XX - lx, YY - ly)
RING, LENS = 13.6 * SX, 9.0 * SX
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
LED_COL = np.array([0.22, 0.62, 1.00], np.float32)
lensOff = np.array([8, 20, 38], np.float32) * (0.55 + 0.45 * np.clip(1 - d / LENS, 0, 1))[..., None]
dome = np.exp(-(((XX - lx + LENS * 0.33) / (LENS * 0.26)) ** 2 + ((YY - ly + LENS * 0.38) / (LENS * 0.20)) ** 2)) * 125
lensOff = lensOff + dome[..., None]
canvas = canvas * (1 - lens[..., None]) + lensOff * lens[..., None]

out = np.clip(canvas, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(ROOT, 'background.jpg'), quality=93, subsampling=0)

# calque d'eclairage de la LED (la facade recoit la lumiere)
RAD = min(220, int(ly) - 2)
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
lmk = np.clip(LENS - dd + 0.5, 0, 1)[..., None]
litL = litL * (1 - lmk) + lensOn * lmk
edge = np.clip((RAD - dd) / (RAD * 0.35), 0, 1) ** 2
a = np.clip((I + halo * 3.0) * 2.2, 0, 1) * edge
a = np.maximum(a, lmk[..., 0])
rgba = np.dstack([np.clip(litL, 0, 255), a * 255]).astype(np.uint8)
Image.fromarray(rgba, 'RGBA').save(os.path.join(ROOT, 'glow_led.png'), optimize=True)

# ------------------------------------------------------------------ 6b. silhouette (boitier + jacks) pour la notice
f8 = out.astype(np.int16)
blue = ((f8[..., 2] - f8[..., 0]) > 22).astype(np.uint8)
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
cnts, _ = cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
SIL = np.zeros((H2F, W2F), np.uint8)
cv2.drawContours(SIL, [max(cnts, key=cv2.contourArea)], -1, 255, -1)
for (x0_, y0_), a_ in ((JL, aL), (JR, aR)):
    h_, w_ = a_.shape
    SIL[y0_:y0_ + h_, x0_:x0_ + w_] = np.maximum(SIL[y0_:y0_ + h_, x0_:x0_ + w_], (a_ * 255).astype(np.uint8))
SIL = cv2.GaussianBlur(cv2.morphologyEx(SIL, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)), (0, 0), 0.8)
Image.fromarray(SIL).save(os.path.join(HERE, 'pedal_mask.png'))

# ------------------------------------------------------------------ 6c. reperes pour le code (unites 760 x 958)
k = 958.0 / HC
rate, depth = U((RATE_C[0], RATE_C[1] + D_KNOBS)), U((DEPTH_C[0], DEPTH_C[1] + D_KNOBS))
mode = U(MODE_C)
led, foot = U(LED_NEW), U((FOOT_CAP[0], to_dst(FOOT_CAP[1])))
def R(b): p0, p1 = U((b[0], b[1])), U((b[2], b[3])); return [round(p0[0], 2), round(p0[1], 2), round(p1[0] - p0[0], 2), round(p1[1] - p0[1], 2)]
info = {
    'rate': rate, 'depth': depth, 'mode': mode, 'knobTop': CAP_R * k, 'knobSkirt': SKIRT_R * k,
    'modeTop': MODE_CAP_R * k, 'modeSkirt': MODE_SKIRT_R * k, 'led': led, 'foot': foot, 'footR': FOOT_NUT_R * k,
    'ledLensR': LENS / 2, 'glowRect': [x0 / 2, y0 / 2, RAD, RAD], 'row': R(ROW), 'bar': R(BAR), 'display': R(DISPLAY),
    'crop': [CX0, CY0, WC, HC],
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
print('ok', WC, HC, CX0, CY0)
