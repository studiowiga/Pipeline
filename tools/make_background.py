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
FOOT_CAP = (558.5, 1237.0)               # centre du bouton du footswitch du visuel (vu en perspective)
FOOT_NUT_R = 74.0
FOOT_HOLE = (559.0, 1236.0, 84.0)        # footswitch du visuel retire (centre, rayon, ombre comprise)
DISPLAY = (287, 903, 833, 1060)
ROW = (300.0, 922.0, 820.0, 990.0)       # ligne d'etat (texte bleu)
BAR = (308.0, 998.0, 808.0, 1046.0)      # barre de presets (cadre garde)
LOGO_BOX = (455, 1302, 664, 1325)

D_KNOBS = 26                              # potards (et leurs graduations / etiquettes) abaisses
MODE_WORD_NEW_Y = 449.0
LED_NEW = (558.0, 124.0)
# remappage du bas (destination <- source) : identite jusqu'a l'ecran, bande de la LED resserree,
# bloc du footswitch rigide, bande sous le footswitch un peu etiree (place du logo), puis tout remonte de 20 px
# bande de la LED (1062-1144) : 44 lignes retirees par « seam carving » (lignes de moindre energie : les bulles et les
# vagues gardent leur forme, pas d'ecrasement) -> footswitch remonte de 44 px ; sous le footswitch, bande du logo etiree
BAND0, BAND1, CARVE = 1062, 1144, 44
FOOT_UP = 28                                    # footswitch d'Echoflex pose 28 px plus haut que l'ancien
UNDER0, UNDER1, UNDER_DST = 1306, 1326, 26      # 20 lignes sous le footswitch -> 26 (place du logo)
LOGO_DST_BOTTOM = None                          # calcule apres le remappage (6 px au-dessus du filet)
TITLE_Y = 787.0                                 # centre du titre PIPELINE : niveau des jacks et des textes IN / OUT
TICK_RATE = (83.0, 94.0)                        # graduations des potards (rayons interieur / exterieur, px du visuel)
TICK_MODE = (62.0, 73.0)

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

def erase_display_text(box, thr=None):
    """ texte de l'ecran efface sans trace : champ lisse interpole entre les bords propres (haut / bas) de la zone,
    multiplie par la trame de points de l'ecran (motif 2 x 2 mesure sur une zone propre), plus le grain """
    global A
    x0, y0, x1, y1 = box
    blur = cv2.GaussianBlur(A, (0, 0), 2.0)
    top = cv2.GaussianBlur(A[y0 - 4:y0, x0 - 10:x1 + 10].mean(0, keepdims=True), (0, 0), sigmaX=6, sigmaY=0.1)[0, 10:-10]
    bot = cv2.GaussianBlur(A[y1:y1 + 4, x0 - 10:x1 + 10].mean(0, keepdims=True), (0, 0), sigmaX=6, sigmaY=0.1)[0, 10:-10]
    t = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    field = top[None] * (1 - t) + bot[None] * t
    cx0, cy0 = DISPLAY[0] + 30, 976                       # zone propre de l'ecran (entre les deux lignes)
    clean = A[cy0:cy0 + 16, cx0:cx0 + 80]
    ratio = clean / np.maximum(cv2.GaussianBlur(clean, (0, 0), 3.0), 1.0)
    top = top / np.maximum(1.0, 1.0); bot = bot
    pat = np.zeros((2, 2, 3), np.float32)
    for yy in range(2):
        for xx in range(2):
            pat[yy, xx] = ratio[(yy - cy0) % 2::2, (xx - cx0) % 2::2].reshape(-1, 3).mean(0)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    P = pat[gy % 2, gx % 2]
    out = field * P + rng.normal(0, 0.8, field.shape).astype(np.float32)
    fe = np.ones((y1 - y0, x1 - x0), np.float32); e = 3
    for i in range(e):
        w = (i + 0.5) / e
        fe[:, i] *= w; fe[:, -1 - i] *= w
    A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - fe[..., None]) + out * fe[..., None]

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

BOXES = {'rlab': (340, 166, 426, 198), 'dlab': (686, 166, 786, 198),     # etiquettes RATE / DEPTH (descendent avec les potards)
         'word': (516, 690, 602, 726), 'led': (486, 1068, 634, 1146)}
KNOB_OF = {'rate': (RATE_C, SKIRT_R, TICK_RATE[1] + 4.0), 'depth': (DEPTH_C, SKIRT_R, TICK_RATE[1] + 4.0),
           'mode': (MODE_C, MODE_SKIRT_R, TICK_MODE[1] + 4.0)}
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
    FILL[k] = f; ALPHA[k] = a * fe
    plate[y0:y1, x0:x1] = plate[y0:y1, x0:x1] * (1 - fe[..., None]) + (f + grain(f.shape)) * fe[..., None]
    if k == 'led':            # les bulles autour de la LED restent : seule la LED et sa lueur disparaissent
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        keep = np.clip((np.hypot(gx - 557.0, gy - 1112.0) - 46.0) / 6.0, 0, 1)
        plate[y0:y1, x0:x1] += (A[y0:y1, x0:x1] - f) * (a * keep)[..., None]

def deshadow(img, c, r, reach=48.0):
    """ ombre portee d'un potard retire (vers le bas a droite) : la facade est ramenee a sa teinte voisine.
    Gain multiplicatif lisse (basse frequence), calcule sur la facade seule (bulles, ecume et textes exclus). """
    cx, cy = c
    R = int(r + reach + 30)
    x0, y0, x1, y1 = int(cx - R), int(cy - R), int(cx + R), int(cy + R)
    reg = img[y0:y1, x0:x1]
    L = lum(reg)
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.hypot(gx - cx - 6.0, gy - cy - 8.0)
    plain = (L < np.median(L) + 15).astype(np.float32)
    low = cv2.GaussianBlur(L * plain, (0, 0), 10) / (cv2.GaussianBlur(plain, (0, 0), 10) + 1e-4)
    ring = (d > r + reach) & (d < r + reach + 26) & (plain > 0)
    ref = np.median(L[ring])
    zone = np.clip((r + reach - d) / 14.0, 0, 1)
    gain = 1 + zone * np.clip(ref / np.maximum(low, 1.0) - 1, 0, 0.9)
    img[y0:y1, x0:x1] = reg * gain[..., None]

def fill_disk(img, c, r):
    """ potard + graduations du visuel effaces : chaque ligne du disque est refaite par interpolation entre la facade
    juste a gauche et juste a droite du disque (echantillons robustes : bulles et traits exclus), grain de la photo """
    cx, cy = c
    out = img.copy()
    for y in range(int(cy - r), int(cy + r) + 1):
        hw = math.sqrt(max(r * r - (y - cy) ** 2, 0.0))
        if hw < 1: continue
        xl, xr = int(cx - hw) - 1, int(cx + hw) + 1
        ys0, ys1 = max(0, y - 3), y + 4
        left = robust_edge(img[ys0:ys1, xl - 10:xl].transpose(1, 0, 2))
        right = robust_edge(img[ys0:ys1, xr + 1:xr + 11].transpose(1, 0, 2))
        cl, cr = np.median(left, 0), np.median(right, 0)
        t = np.linspace(0, 1, xr - xl + 1, dtype=np.float32)[:, None]
        out[y, xl:xr + 1] = cl * (1 - t) + cr * t
    gy, gx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float32)
    dd = np.hypot(gx - cx, gy - cy)
    m = np.clip((r - dd) / 3.0, 0, 1)[..., None]
    smooth = cv2.GaussianBlur(out, (0, 0), sigmaX=1.5, sigmaY=3.0)
    out = smooth + grain(out.shape)
    img[:] = img * (1 - m) + out * m

def clean_knob(img, c, r_clear, r_zone, shift):
    """ potard, graduations, reflets et ombre portee du visuel retires :
      - facade modelisee par une surface quadratique ajustee sur la facade unie autour (bulles, vagues, textes exclus),
      - disque interieur (potard + graduations) : facade modelisee + grain,
      - zone de l'ombre (decalee vers le bas a droite) : facade modelisee, les traits clairs (bulles, textes) gardes. """
    cx, cy = c
    R = int(r_zone + max(shift) + 60)
    x0, y0, x1, y1 = int(cx - R), int(cy - R), int(cx + R), int(cy + R)
    reg = img[y0:y1, x0:x1].copy()
    L = lum(reg)
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d0 = np.hypot(gx - cx, gy - cy)
    ds = np.hypot(gx - cx - shift[0], gy - cy - shift[1])      # ombre longue et douce, portee vers le bas a droite
    medL = np.median(L[(d0 > r_zone + 8)])
    plain = (d0 > r_zone + 8) & (ds > r_zone + 8) & (np.abs(L - medL) < 14)
    u, v = (gx - cx) / R, (gy - cy) / R
    Mx = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], -1)
    fit = np.zeros_like(reg)
    for ch in range(3):
        coef, *_ = np.linalg.lstsq(Mx[plain], reg[..., ch][plain], rcond=None)
        fit[..., ch] = Mx @ coef
    # ombre : correction multiplicative basse frequence (gain = facade modelisee / facade reelle lissee), appliquee a tout
    # (grain de la photo, bulles, etiquettes gardes), fondu tres large -> aucun cercle visible
    notBright = ((L < lum(fit) + 15) & (d0 > r_clear + 3)).astype(np.float32)
    lowReal = cv2.GaussianBlur(reg * notBright[..., None], (0, 0), 7) / (cv2.GaussianBlur(notBright, (0, 0), 7)[..., None] + 1e-4)
    g = np.clip(lum(fit) / np.maximum(lum(lowReal), 1.0), 0.85, 3.0)[..., None]   # gain de luminance (pas de teinte sur les bulles)
    w = np.clip((r_zone + 40.0 - ds) / 60.0, 0, 1)
    w = w * w * (3 - 2 * w)
    w = w * ((gx > 246) & (gx < 872)).astype(np.float32)          # jamais hors de la facade (filet, tranche, mur)
    w = cv2.GaussianBlur(w, (0, 0), 2.0)
    gw = 1 + (g - 1) * w[..., None]
    corr = reg * gw + (fit - lowReal * gw) * w[..., None]
    # ombre profonde (pres du potard) : la photo n'a plus d'information utile -> facade modelisee + grain
    gl = cv2.GaussianBlur(lum(fit) / np.maximum(lum(lowReal), 1.0), (0, 0), 4)
    feat = np.clip((L - lum(fit) - 18.0) / 18.0, 0, 1)
    feat = cv2.GaussianBlur(cv2.dilate(feat, np.ones((7, 7), np.uint8)), (0, 0), 1.5)        # bulles entieres (bords compris)
    deep = (np.clip((gl - 1.25) / 0.6, 0, 1) * w * (1 - np.clip(feat * 1.5, 0, 1)))[..., None]
    corr = corr * (1 - deep) + (fit + grain(reg.shape)) * deep
    # disque du potard et des graduations : facade modelisee + grain (le plugin y dessine le potard et les traits)
    inner = np.clip((r_clear - d0) / 4.0, 0, 1)[..., None]
    out = corr * (1 - inner) + (fit + grain(reg.shape)) * inner
    img[y0:y1, x0:x1] = out

# zones d'ombre mesurees sur le visuel (profils radiaux) : ~170 px vers le bas a droite pour RATE / DEPTH, ~145 pour MODE
clean_knob(plate, RATE_C, KNOB_OF['rate'][2], 145.0, (25.0, 33.0))
clean_knob(plate, DEPTH_C, KNOB_OF['depth'][2], 145.0, (25.0, 33.0))
clean_knob(plate, MODE_C, KNOB_OF['mode'][2], 112.0, (20.0, 26.0))

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

paste_delta(plate, 'rlab', 0, D_KNOBS)
paste_delta(plate, 'dlab', 0, D_KNOBS)

# textes IN / OUT : effaces a leur place (matte blanc garde) pour etre recolles au niveau du titre
IO_BOX = {'out': (241, 434, 278, 462), 'in': (852, 432, 877, 464)}   # sans le filet du cadre
IO_ALPHA = {}
for k, (x0, y0, x1, y1) in IO_BOX.items():
    reg = plate[y0:y1, x0:x1].copy()
    m = cv2.dilate((lum(reg) > 150).astype(np.uint8), np.ones((5, 5), np.uint8))
    bg = cv2.inpaint(np.clip(reg, 0, 255).astype(np.uint8), m, 3, cv2.INPAINT_TELEA).astype(np.float32)
    IO_ALPHA[k] = np.clip((lum(reg) - lum(bg)) / np.maximum(235.0 - lum(bg), 30.0), 0, 1) * (m > 0)
    plate[y0:y1, x0:x1] = np.where(m[..., None] > 0, bg + grain(bg.shape, 1.5), reg)
wb = BOXES['word']
paste_delta(plate, 'word', 0, int(round(MODE_WORD_NEW_Y - (wb[1] + wb[3]) / 2)))

# footswitch du visuel (vu en perspective) retire : vagues reprises a cote, sur les memes lignes (meilleur raccord)
def remove_footswitch(img):
    cx, cy, r = FOOT_HOLE
    R = int(r + 26)
    y0, y1, x0, x1 = int(cy - R), int(cy + R), int(cx - R), int(cx + R)
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.hypot(gx - cx, gy - cy)
    ring = (d > r) & (d < r + 22)
    best, bestErr = None, 1e18
    for dx in list(range(-330, -170, 6)) + list(range(170, 330, 6)):
        if x0 + dx < 250 or x1 + dx > 868: continue
        donor = img[y0:y1, x0 + dx:x1 + dx]
        err = ((donor - img[y0:y1, x0:x1]) ** 2).sum(-1)[ring].mean()
        if err < bestErr: best, bestErr = dx, err
    donor = img[y0:y1, x0 + best:x1 + best]
    m = np.clip((r + 10 - d) / 12.0, 0, 1)[..., None]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - m) + donor * m
    return best
FOOT_DONOR = remove_footswitch(plate)

# ------------------------------------------------------------------ 4. footswitch remonte : seam carving dans la bande de la LED
def carve_rows(img, n):
    """ retire n lignes « de couture » horizontales de moindre energie (gradient + bulles claires penalisees) """
    img = img.copy()
    for _ in range(n):
        Lg = lum(img)
        gxx = cv2.Sobel(Lg, cv2.CV_32F, 1, 0, ksize=3); gyy = cv2.Sobel(Lg, cv2.CV_32F, 0, 1, ksize=3)
        en = np.abs(gxx) + np.abs(gyy) + np.clip(Lg - 110.0, 0, None) * 2.0
        h, w = en.shape
        M = en.copy(); back = np.zeros((h, w), np.int8)
        for x in range(1, w):
            prev = M[:, x - 1]
            up = np.r_[np.inf, prev[:-1]]; dn = np.r_[prev[1:], np.inf]
            stack = np.vstack([up, prev, dn])
            arg = np.argmin(stack, 0)
            M[:, x] += stack[arg, np.arange(h)]
            back[:, x] = arg - 1
        y = int(np.argmin(M[:, -1]))
        keep = np.ones((h, w), bool)
        for x in range(w - 1, -1, -1):
            keep[y, x] = False
            y = int(np.clip(y + back[y, x], 0, h - 1))
        img = img.transpose(1, 0, 2)[keep.T].reshape(w, h - 1, 3).transpose(1, 0, 2)
    return img

strip = carve_rows(plate[BAND0:BAND1], CARVE)
below = plate[BAND1:]
# sous le footswitch : 20 lignes -> 26 (interpolation verticale douce), le reste remonte d'un bloc
u0, u1 = UNDER0 - BAND1, UNDER1 - BAND1
under = cv2.resize(below[u0:u1], (W, UNDER_DST), interpolation=cv2.INTER_CUBIC)
P2 = np.concatenate([plate[:BAND0], strip, below[:u0], under, below[u1:]], axis=0)
def to_dst(y):                                            # ligne source -> ligne destination (pour les reperes)
    if y < BAND0: return float(y)
    if y < BAND1: return BAND0 + (y - BAND0) * (BAND1 - BAND0 - CARVE) / (BAND1 - BAND0)
    if y < UNDER0: return float(y - CARVE)
    if y < UNDER1: return UNDER0 - CARVE + (y - UNDER0) * UNDER_DST / (UNDER1 - UNDER0)
    return float(y - CARVE + UNDER_DST - (UNDER1 - UNDER0))
LOGO_DST_BOTTOM = int(round(to_dst(1326))) - 6

# logo recolle (blanc du visuel) au-dessus du filet
la = logo_alpha
ny0 = LOGO_DST_BOTTOM - la.shape[0] + 1 + 2
reg = P2[ny0:ny0 + la.shape[0], lx0:lx1]
P2[ny0:ny0 + la.shape[0], lx0:lx1] = reg * (1 - la[..., None]) + np.array([236, 238, 236], np.float32) * la[..., None]

# textes IN / OUT au niveau du titre (leger halo sombre : lisibles sur l'ecume des vagues)
for k, (x0, y0, x1, y1) in IO_BOX.items():
    a_ = IO_ALPHA[k]
    ny = int(round(TITLE_Y - (y1 - y0) / 2))
    dx = 7 if k == 'out' else -2                          # un peu d'air entre le texte et le filet du cadre
    x0, x1 = x0 + dx, x1 + dx
    reg = P2[ny:ny + (y1 - y0), x0:x1]
    sh_ = np.roll(np.roll(cv2.GaussianBlur(a_, (0, 0), 0.8), 1, 0), 1, 1)          # fine ombre portee, pas de halo
    reg = reg * (1 - 0.40 * sh_ * (1 - a_))[..., None]
    P2[ny:ny + (y1 - y0), x0:x1] = reg * (1 - a_[..., None]) + np.array([236, 238, 236], np.float32) * a_[..., None]

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

# ------------------------------------------------------------------ 5a. graduations des potards (redessinees, nettes)
from PIL import ImageDraw
SS = 4
def draw_ticks(centre, r0, r1, angles, width):
    """ traits blancs du visuel, dessines en supersampling ; legere ombre portee vers le bas a droite """
    global canvas
    cx, cy = T(centre)
    k = SY                                                   # cercle (le potard est rond, il n'est pas etire)
    pad = int(r1 * k + 12)
    x0, y0 = int(cx - pad), int(cy - pad)
    size = 2 * pad
    im = Image.new('L', (size * SS, size * SS), 0)
    dr = ImageDraw.Draw(im)
    for a in angles:
        t = math.radians(a)
        p0 = ((cx - x0 + r0 * k * math.sin(t)) * SS, (cy - y0 - r0 * k * math.cos(t)) * SS)
        p1 = ((cx - x0 + r1 * k * math.sin(t)) * SS, (cy - y0 - r1 * k * math.cos(t)) * SS)
        dr.line([p0, p1], fill=255, width=int(round(width * k * SS)))
    al = np.asarray(im.resize((size, size), Image.LANCZOS)).astype(np.float32) / 255
    sh = np.roll(np.roll(cv2.GaussianBlur(al, (0, 0), 1.0), 2, 0), 1, 1)
    reg = canvas[y0:y0 + size, x0:x0 + size]
    reg = reg * (1 - 0.30 * sh * (1 - al))[..., None]
    canvas[y0:y0 + size, x0:x0 + size] = reg * (1 - al[..., None]) + np.array([226, 229, 227], np.float32) * al[..., None]

draw_ticks((RATE_C[0], RATE_C[1] + D_KNOBS), *TICK_RATE, [-150 + 30 * i for i in range(11)], 2.6)
draw_ticks((DEPTH_C[0], DEPTH_C[1] + D_KNOBS), *TICK_RATE, [-150 + 30 * i for i in range(11)], 2.6)
draw_ticks(MODE_C, *TICK_MODE, [-150 + 300.0 / 7.0 * i for i in range(8)], 2.6)

# ------------------------------------------------------------------ 5a'. footswitch d'ECHOFLEX (vue de dessus, photo detouree, ombres comprises)
FOOT_NEW = (FOOT_HOLE[0], to_dst(FOOT_HOLE[1]) - FOOT_UP)
fsimg = Image.open(os.path.join(HERE, 'fs_echoflex.png')).convert('RGBA')
fsc = (FOOT_NUT_R * 2.0 * SY) / 247.0                    # 247 px = largeur de l'ecrou dans le sprite
fsimg = fsimg.resize((round(fsimg.width * fsc), round(fsimg.height * fsc)), Image.LANCZOS)
fa = np.asarray(fsimg).astype(np.float32) / 255
fcx, fcy = T(FOOT_NEW)
ox, oy = int(round(fcx - 199.5 * fsc)), int(round(fcy - 198.0 * fsc))
h_, w_ = fa.shape[:2]
canvas[oy:oy + h_, ox:ox + w_] = canvas[oy:oy + h_, ox:ox + w_] * (1 - fa[..., 3:]) + fa[..., :3] * 255 * fa[..., 3:]

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
JACK_Y = T((0, TITLE_Y))[1]
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

# fond derriere la pedale assombri (mur), la pedale et ses jacks ne changent pas
_f = np.clip(canvas, 0, 255).astype(np.int16)
_blue = ((_f[..., 2] - _f[..., 0]) > 22).astype(np.uint8)
_blue = cv2.morphologyEx(_blue, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
_c, _ = cv2.findContours(_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
_ped = np.zeros((H2F, W2F), np.uint8); cv2.drawContours(_ped, [max(_c, key=cv2.contourArea)], -1, 255, -1)
for (x0_, y0_), a_ in ((JL, aL), (JR, aR)):
    hh, ww = a_.shape
    _ped[y0_:y0_ + hh, x0_:x0_ + ww] = np.maximum(_ped[y0_:y0_ + hh, x0_:x0_ + ww], (a_ * 255).astype(np.uint8))
_ped = cv2.GaussianBlur(cv2.dilate(_ped, np.ones((3, 3), np.uint8)).astype(np.float32) / 255, (0, 0), 1.0)
canvas = canvas * (1 - (1 - _ped) * 0.52)[..., None]

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
led, foot = U(LED_NEW), U(FOOT_NEW)
def R(b): p0, p1 = U((b[0], b[1])), U((b[2], b[3])); return [round(p0[0], 2), round(p0[1], 2), round(p1[0] - p0[0], 2), round(p1[1] - p0[1], 2)]
info = {
    'rate': rate, 'depth': depth, 'mode': mode, 'knobTop': CAP_R * k, 'knobSkirt': SKIRT_R * k,
    'modeTop': MODE_CAP_R * k, 'modeSkirt': MODE_SKIRT_R * k, 'led': led, 'foot': foot, 'footR': FOOT_NUT_R * k * 0.92,
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
