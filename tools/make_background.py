"""
PIPELINE (Studio Wiga) - fond PROVISOIRE du plugin (en attendant le visuel de l'utilisateur).

Rendu procedural dans le cadre 1520 x 1916 px (= 2 x repere 760 x 958 du plugin), une seule lumiere
(en haut a gauche, comme toutes les pedales Studio Wiga) :
  1. fond sombre + boitier Hammond 125B (proportions de l'Aqueduct : 121 x 64 mm) bleu anodise, chanfreins eclaires,
  2. corps des potards RATE / DEPTH et du selecteur MODE (champ de hauteurs + eclairage + ombre portee) :
     seuls les reperes sont dessines par le plugin et tournent,
  3. serigraphie (titres, 8 positions du selecteur), ecran noir (ligne d'etat + barre de presets),
  4. LED eteinte + calque d'eclairage de la facade (canal alpha), footswitch d'ECHOFLEX, jacks du kit (IN a droite, OUT a gauche),
  5. ecrit Layout.h (reperes en unites 760 x 958), tools/layout.json, tools/pedal_mask.png (silhouette pour la notice).

Quand le visuel definitif arrive, ce script est remplace par un traitement du visuel (comme FreakOut / Doorn)
qui ecrit les memes fichiers : le code C++ n'a pas a changer.

Usage : python3 tools/make_background.py
"""
import os, json, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, 'assets', 'fonts')
W2, H2 = 1520, 1916
rng = np.random.default_rng(11)

L = np.array([-0.46, -0.62, 0.64]); L /= np.linalg.norm(L)
V = np.array([0.0, 0.0, 1.0]); Hh = (L + V) / np.linalg.norm(L + V)

def U2(v): return v * 2.0          # unites -> px

# ------------------------------------------------------------------ reperes (unites 760 x 958)
BOX = (150.0, 30.0, 610.0, 905.0)                 # boitier (x0, y0, x1, y1)
BOX_R = 26.0
KNOBS = {'rate': (262.0, 196.0), 'depth': (498.0, 196.0)}
KNOB_TOP, KNOB_SKIRT = 37.0, 50.0
MODE_C = (380.0, 390.0); MODE_TOP, MODE_SKIRT = 27.0, 35.0
MODE_LABEL_R = 72.0
LED = (380.0, 748.0)
FOOT = (380.0, 828.0)
DISPLAY = (196.0, 606.0, 564.0, 712.0)
ROW = (204.0, 614.0, 556.0, 662.0)                # ligne d'etat
BAR = (212.0, 670.0, 548.0, 702.0)                # barre de presets
TITLE_Y = 532.0

# ------------------------------------------------------------------ outils
YY, XX = np.mgrid[0:H2, 0:W2].astype(np.float32)

def rrect_sdf(x0, y0, x1, y1, r):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(XX - cx) - hx, np.abs(YY - cy) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r   # < 0 dedans

def shade(n, albedo, spec=0.0, shin=30.0, amb=0.30):
    nl = np.clip(n @ L, 0, 1)
    nh = np.clip(n @ Hh, 0, 1)
    return albedo * (amb + (1 - amb) * nl)[..., None] + (spec * nh ** shin)[..., None] * 255

def font(name, px): return ImageFont.truetype(os.path.join(FONTS, name), int(round(px)))

# ------------------------------------------------------------------ 1. fond (pierre sombre) + ombre du boitier
base = 26 + 10 * np.clip(1.15 - np.hypot((XX - 500) / W2, (YY - 400) / H2) * 1.4, 0, 1)
grain = cv2.GaussianBlur(rng.normal(0, 1, (H2, W2)).astype(np.float32), (0, 0), 1.2) * 3.0
canvas = np.repeat((base + grain)[..., None], 3, axis=2) * np.array([0.95, 0.98, 1.04])

bx0, by0, bx1, by1 = [U2(v) for v in BOX]
sd = rrect_sdf(bx0, by0, bx1, by1, U2(BOX_R))
shadow = cv2.GaussianBlur((rrect_sdf(bx0 + 22, by0 + 34, bx1 + 22, by1 + 34, U2(BOX_R)) < 0).astype(np.float32), (0, 0), 26)
canvas *= (1 - 0.72 * shadow)[..., None]
contact = cv2.GaussianBlur((rrect_sdf(bx0 + 5, by0 + 8, bx1 + 5, by1 + 8, U2(BOX_R)) < 0).astype(np.float32), (0, 0), 6)
canvas *= (1 - 0.45 * contact)[..., None]

# ------------------------------------------------------------------ 2. jacks du kit (sous le boitier : ils sortent des tranches)
def paste_rgba(img, cx, top, flip_y=False):
    global canvas
    a = np.asarray(img).astype(np.float32) / 255
    h_, w_ = a.shape[:2]
    x0, y0 = int(round(cx - w_ / 2)), int(round(top))
    al = a[..., 3:]
    reg = canvas[y0:y0 + h_, x0:x0 + w_]
    canvas[y0:y0 + h_, x0:x0 + w_] = reg * (1 - al) + a[..., :3] * 255 * al
    return x0, y0, w_, h_

jack_out = Image.open(os.path.join(ROOT, 'assets', 'kit', 'embase_jack_gauche_OUT.png')).convert('RGBA')
jack_in = Image.open(os.path.join(ROOT, 'assets', 'kit', 'embase_jack_droite_IN.png')).convert('RGBA')
JACK_Y = U2(300.0)
# l'embase sort de la tranche : ~13 unites visibles, le reste passe sous le boitier
jo = paste_rgba(jack_out, bx0 - 19, JACK_Y - jack_out.height / 2)
ji = paste_rgba(jack_in, bx1 + 19, JACK_Y - jack_in.height / 2)

# ------------------------------------------------------------------ 3. boitier bleu anodise
inside = np.clip(-sd, 0, None)
EDGE = 20.0
t = np.clip(inside / EDGE, 0, 1)
hgt = EDGE * (1 - (1 - t) ** 2) * 0.9                 # chanfrein arrondi
gy, gx = np.gradient(cv2.GaussianBlur(hgt, (0, 0), 1.0))
n = np.dstack([-gx, -gy, np.ones_like(hgt)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
blue = np.array([38, 92, 142], np.float32)             # bleu « eau profonde »
# poudre anodisee : grain fin + legere variation basse frequence
pow_ = cv2.GaussianBlur(rng.normal(0, 1, (H2, W2)).astype(np.float32), (0, 0), 0.8) * 0.035 \
     + cv2.GaussianBlur(rng.normal(0, 1, (H2, W2)).astype(np.float32), (0, 0), 40) * 0.6
albedo = blue[None, None, :] * (1 + pow_[..., None])
lit = shade(n, albedo, spec=0.20, shin=18, amb=0.38)
# eclairage global de la face : plus clair vers la lumiere (haut gauche)
grad = 1.08 - 0.16 * ((XX - bx0) / (bx1 - bx0) * 0.45 + (YY - by0) / (by1 - by0) * 0.55)
lit *= grad[..., None]
# reflet doux du vernis vers le haut gauche
sheen = np.exp(-(((XX - bx0 - 260) / 520) ** 2 + ((YY - by0 - 300) / 700) ** 2)) * 18
lit += sheen[..., None]
aa = np.clip(-sd + 0.5, 0, 1)[..., None]
canvas = canvas * (1 - aa) + lit * aa
SIL = np.clip(-sd + 0.5, 0, 1)

# ------------------------------------------------------------------ 4. serigraphie (blanc casse) et filet du cadre
ink = Image.new('L', (W2, H2), 0)
dr = ImageDraw.Draw(ink)
def text_c(s, cx, cy, f, spacing=0):
    if spacing:
        widths = [dr.textlength(ch, font=f) for ch in s]
        total = sum(widths) + spacing * (len(s) - 1)
        x = cx - total / 2
        for ch, w_ in zip(s, widths):
            dr.text((x, cy), ch, font=f, fill=255, anchor='lm'); x += w_ + spacing
    else:
        dr.text((cx, cy), s, font=f, fill=255, anchor='mm')

# filet grave a 26 unites du bord
fr = 14
dr.rounded_rectangle([bx0 + U2(fr), by0 + U2(fr), bx1 - U2(fr), by1 - U2(fr)], radius=U2(BOX_R - 8), outline=150, width=3)
fl = font('BarlowCondensed-Bold.ttf', U2(17))
for k, (x, y) in KNOBS.items():
    text_c(k.upper(), U2(x), U2(y - KNOB_SKIRT - 24), fl, spacing=U2(3.2))
    # graduations min / max autour des potards
    for i in range(11):
        a = math.radians(-150 + 30 * i)
        r0, r1 = KNOB_SKIRT + 7, KNOB_SKIRT + (14 if i in (0, 5, 10) else 11)
        dr.line([U2(x + r0 * math.sin(a)), U2(y - r0 * math.cos(a)), U2(x + r1 * math.sin(a)), U2(y - r1 * math.cos(a))], fill=210, width=3)
fm = font('BarlowCondensed-SemiBold.ttf', U2(13.5))
mx, my = MODE_C
names = ['SINE', 'TRI', 'RAMP', 'SQR', 'RAND', 'ENV D', 'ENV R', 'ENV P']
MODE_ANGLES = [-150 + k * 300 / 7 for k in range(8)]
for k, nm in enumerate(names):
    a = math.radians(MODE_ANGLES[k])
    r0, r1 = MODE_SKIRT + 6, MODE_SKIRT + 13
    dr.line([U2(mx + r0 * math.sin(a)), U2(my - r0 * math.cos(a)), U2(mx + r1 * math.sin(a)), U2(my - r1 * math.cos(a))], fill=225, width=4)
    lr = MODE_LABEL_R + (6 if abs(math.sin(a)) > 0.8 else 0)
    text_c(nm, U2(mx + lr * math.sin(a)), U2(my - lr * math.cos(a)), fm, spacing=U2(1.0))
text_c('MODE', U2(mx), U2(my + 84), fl, spacing=U2(3.2))
# IN / OUT a la hauteur des jacks, centres sur leur axe
fio = font('BarlowCondensed-Bold.ttf', U2(13))
text_c('OUT', U2(BOX[0] + 26), U2(300.0), fio, spacing=U2(1.5))
text_c('IN', U2(BOX[2] - 24), U2(300.0), fio, spacing=U2(1.5))
# titre + sous-titre + vague (le « tuyau » qui ondule)
ft = font('BebasNeue-Regular.ttf', U2(84))
text_c('PIPELINE', U2(380), U2(TITLE_Y), ft, spacing=U2(5))
fs_ = font('BarlowCondensed-Medium.ttf', U2(15))
text_c('PITCH VIBRATO', U2(380), U2(TITLE_Y + 47), fs_, spacing=U2(6.5))
wave = [(U2(214 + i * 0.5), U2(TITLE_Y + 47) + U2(4.2) * math.sin(i * 0.5 / 9.0)) for i in range(0, 2 * 62)]
dr.line(wave, fill=200, width=3, joint='curve')
wave = [(U2(484 + i * 0.5), U2(TITLE_Y + 47) + U2(4.2) * math.sin(i * 0.5 / 9.0 + 1.3)) for i in range(0, 2 * 62)]
dr.line(wave, fill=200, width=3, joint='curve')
inkA = np.asarray(ink.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255
# encre legerement en relief : ombre fine vers le bas droite, encre claire
sh_ = np.roll(np.roll(inkA, 2, 0), 1, 1)
canvas *= (1 - 0.25 * sh_ * (1 - inkA))[..., None]
inkCol = np.array([236, 238, 234], np.float32) * (0.93 + 0.07 * grad[..., None])
canvas = canvas * (1 - inkA[..., None]) + inkCol * inkA[..., None]
TITLE_ALPHA = inkA

# ------------------------------------------------------------------ 5. ecran (verre noir) : ligne d'etat + barre de presets
dx0, dy0, dx1, dy1 = [U2(v) for v in DISPLAY]
dsd = rrect_sdf(dx0, dy0, dx1, dy1, U2(9))
bezel = np.clip(-rrect_sdf(dx0 - 7, dy0 - 7, dx1 + 7, dy1 + 7, U2(12)) + 0.5, 0, 1)
canvas *= (1 - 0.35 * cv2.GaussianBlur(bezel, (0, 0), 5))[..., None]
glass = np.clip(-dsd + 0.5, 0, 1)
gcol = np.dstack([np.full((H2, W2), 9.0), np.full((H2, W2), 11.0), np.full((H2, W2), 14.0)])
refl = np.clip((dy0 + (dy1 - dy0) * 0.42 - YY) / ((dy1 - dy0) * 0.42), 0, 1) ** 2 * 14
gcol += refl[..., None]
inner = cv2.GaussianBlur((dsd < -6).astype(np.float32), (0, 0), 5)
gcol *= (0.55 + 0.45 * inner)[..., None]
rim = np.exp(-((dsd + 1.0) / 1.4) ** 2)
lightside = np.clip(((XX - (dx0 + dx1) / 2) * 0.4 + (YY - (dy0 + dy1) / 2)) / 120, -1, 1)
canvas = canvas * (1 - glass[..., None]) + gcol * glass[..., None]
canvas += (rim * np.clip(lightside, 0, 1) * 70)[..., None]       # arete basse eclairee
canvas *= (1 - rim * np.clip(-lightside, 0, 1) * 0.6)[..., None]
# cadre fin de la barre de presets
bar = Image.new('L', (W2, H2), 0)
ImageDraw.Draw(bar).rounded_rectangle([U2(BAR[0]), U2(BAR[1]), U2(BAR[2]), U2(BAR[3])], radius=U2(5), outline=255, width=2)
ImageDraw.Draw(bar).line([U2(ROW[0] + 14), U2(666), U2(ROW[2] - 14), U2(666)], fill=120, width=2)
barA = np.asarray(bar).astype(np.float32) / 255
canvas = canvas * (1 - 0.35 * barA[..., None]) + np.array([140, 170, 190]) * 0.35 * barA[..., None]

# ------------------------------------------------------------------ 6. potards (champ de hauteurs supersample x3)
def render_knob(cx_u, cy_u, r_top, r_skirt, flutes, top_h=22.0, skirt_h=12.0):
    """ corps de potard noir : jupe moletee + chapeau ; pas de repere (dessine par le plugin) """
    global canvas, SIL
    SS = 3
    R = r_skirt + 26
    size = int(round(U2(R) * 2))
    yy, xx = np.mgrid[0:size * SS, 0:size * SS].astype(np.float32)
    x = (xx + 0.5) / SS - size / 2; y = (yy + 0.5) / SS - size / 2
    r = np.hypot(x, y); th = np.arctan2(y, x)
    rs = U2(r_skirt) * (1 + 0.018 * np.cos(flutes * th))          # moletage
    rt = U2(r_top)
    # jupe : cone bas de profil arrondi
    hs = np.where(r < rs, U2(skirt_h) * np.clip((rs - r) / U2(5.0), 0, 1) ** 0.6, 0.0)
    # chapeau : plateau avec arete arrondie, legere concavite
    edge = np.clip((rt - r) / U2(6.0), 0, 1)
    hc = np.where(r < rt, U2(top_h) * (1 - (1 - edge) ** 2) - 0.0008 * (rt - r) * (rt - r) / rt * 40, 0.0)
    flutes_top = np.where((r < rt * 1.0) & (r > rt * 0.93), 0.0, 0.0)
    h = np.maximum(hs, hc + flutes_top)
    gy_, gx_ = np.gradient(h)
    nn = np.dstack([-gx_, -gy_, np.ones_like(h)]); nn /= np.linalg.norm(nn, axis=2, keepdims=True)
    alb = np.full(h.shape + (3,), 13.0)
    alb[r >= rt - 0.5] = 17.0
    col = shade(nn, alb, spec=0.55, shin=26, amb=0.25)
    # reflet doux circulaire du chapeau (plastique satine)
    hl = np.exp(-(((x + rt * 0.35) / (rt * 0.42)) ** 2 + ((y + rt * 0.42) / (rt * 0.30)) ** 2)) * (r < rt - 4)
    col += (hl * 26)[..., None]
    mask = (h > 0.01).astype(np.float32)
    col = cv2.resize(col, (size, size), interpolation=cv2.INTER_AREA)
    mask = cv2.resize(mask, (size, size), interpolation=cv2.INTER_AREA)
    cx2, cy2 = U2(cx_u), U2(cy_u)
    x0, y0 = int(round(cx2 - size / 2)), int(round(cy2 - size / 2))
    reg = canvas[y0:y0 + size, x0:x0 + size]
    # ombre portee (vers le bas droite, d'autant plus longue que la piece est haute) + ombre de contact
    sh1 = cv2.GaussianBlur(np.roll(np.roll(mask, 16, 0), 11, 1), (0, 0), 10)
    sh2 = cv2.GaussianBlur(np.roll(np.roll(mask, 4, 0), 3, 1), (0, 0), 3)
    reg = reg * (1 - 0.55 * sh1 - 0.35 * sh2)[..., None]
    canvas[y0:y0 + size, x0:x0 + size] = reg * (1 - mask[..., None]) + col * mask[..., None]

for k, c in KNOBS.items():
    render_knob(*c, KNOB_TOP, KNOB_SKIRT, 40)
render_knob(*MODE_C, MODE_TOP, MODE_SKIRT, 28, top_h=18, skirt_h=9)

# ------------------------------------------------------------------ 7. LED (eteinte) : bague chromee, gorge, lentille sombre
lx, ly = U2(LED[0]), U2(LED[1])
d = np.hypot(XX - lx, YY - ly)
RING, LENS = U2(9.5), U2(6.2)
ring = np.clip(RING - d + 0.5, 0, 1) * np.clip(d - LENS + 0.5, 0, 1)
ang = np.arctan2(YY - ly, XX - lx)
ringLight = 0.5 + 0.5 * np.cos(ang - math.atan2(-0.62, -0.46))                 # clair vers le haut gauche
ringCol = (60 + 170 * ringLight ** 1.5)[..., None] * np.array([1.0, 1.0, 1.02])
canvas *= (1 - 0.5 * cv2.GaussianBlur((d < RING).astype(np.float32), (0, 0), 3)[..., None] * (np.hypot(XX - lx - 5, YY - ly - 7) < RING + 6)[..., None])
canvas = canvas * (1 - ring[..., None]) + ringCol * ring[..., None]
lens = np.clip(LENS - d + 0.5, 0, 1)
LED_COL = np.array([0.20, 0.78, 1.00], np.float32)                           # bleu cyan (eau)
lensOff = (np.array([10, 28, 40], np.float32) * (0.6 + 0.4 * np.clip(1 - d / LENS, 0, 1))[..., None])
dome = np.exp(-(((XX - lx + LENS * 0.35) / (LENS * 0.28)) ** 2 + ((YY - ly + LENS * 0.40) / (LENS * 0.22)) ** 2)) * 120
lensOff = lensOff + dome[..., None]
canvas = canvas * (1 - lens[..., None]) + lensOff * lens[..., None]

# ------------------------------------------------------------------ 8. footswitch d'ECHOFLEX (photo detouree, ombres comprises)
fsimg = Image.open(os.path.join(HERE, 'fs_echoflex.png')).convert('RGBA')
FS_SCALE = 0.74
fsimg = fsimg.resize((round(fsimg.width * FS_SCALE), round(fsimg.height * FS_SCALE)), Image.LANCZOS)
fx, fy = U2(FOOT[0]), U2(FOOT[1])
paste_rgba(fsimg, fx, fy - fsimg.height / 2)

# ------------------------------------------------------------------ 9. logo Studio Wiga (blanc)
logo = Image.open(os.path.join(ROOT, 'assets', 'logo_studio_wiga_blanc.png')).convert('RGBA')
lw = U2(132); logo = logo.resize((int(lw), int(lw * logo.height / logo.width)), Image.LANCZOS)
la = np.asarray(logo).astype(np.float32) / 255
lx0, ly0 = int(U2(380) - logo.width / 2), int(U2(884) - logo.height / 2)
reg = canvas[ly0:ly0 + logo.height, lx0:lx0 + logo.width]
canvas[ly0:ly0 + logo.height, lx0:lx0 + logo.width] = reg * (1 - la[..., 3:] * 0.95) + np.array([234, 236, 232]) * la[..., 3:] * 0.95

# silhouette pour la notice (boitier + jacks)
for (x0, y0, w_, h_), img in ((jo, jack_out), (ji, jack_in)):
    SIL[y0:y0 + h_, x0:x0 + w_] = np.maximum(SIL[y0:y0 + h_, x0:x0 + w_], np.asarray(img)[..., 3] / 255.0)
Image.fromarray((SIL * 255).astype(np.uint8)).save(os.path.join(HERE, 'pedal_mask.png'))

out = np.clip(canvas, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(ROOT, 'background.jpg'), quality=93, subsampling=0)

# ------------------------------------------------------------------ 10. calque d'eclairage de la LED (la facade recoit la lumiere)
RAD = 230
x0, y0 = int(round(lx - RAD)), int(round(ly - RAD))
sub = canvas[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD].copy()
gy2, gx2 = np.mgrid[0:2 * RAD, 0:2 * RAD].astype(np.float32)
dd = np.hypot(gx2 + x0 - lx, gy2 + y0 - ly)
def lamb(h): return (h * h / (h * h + dd * dd)) ** 1.5
I = 1.30 * lamb(16) + 0.30 * lamb(70) + 0.09 * lamb(170)
halo = 0.10 * lamb(26)
litL = sub * (1 + I[..., None] * LED_COL * 2.4) + halo[..., None] * LED_COL * 255
# lentille allumee : coeur presque blanc, corps sature, bord plus sombre, reflet fixe
dl = dd
core = np.clip(1 - dl / LENS, 0, 1)
lensOn = (LED_COL * 255)[None, None, :] * (0.55 + 0.45 * core[..., None]) + (np.clip(core * 1.8 - 0.9, 0, 1) ** 1.5 * 255)[..., None] * (1 - LED_COL * 0.3)
lensOn += (dome[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD] * 0.6)[..., None]
lm = np.clip(LENS - dl + 0.5, 0, 1)[..., None]
litL = litL * (1 - lm) + lensOn * lm
edge = np.clip((RAD - dd) / (RAD * 0.35), 0, 1) ** 2
a = np.clip((I + halo * 3.0) * 2.2, 0, 1) * edge
a = np.maximum(a, lm[..., 0])
# les potards et le footswitch n'en recoivent que peu : limite par la luminosite deja la (le noir reste noir)
rgba = np.dstack([np.clip(litL, 0, 255), a * 255]).astype(np.uint8)
Image.fromarray(rgba, 'RGBA').save(os.path.join(ROOT, 'glow_led.png'), optimize=True)

# ------------------------------------------------------------------ 11. reperes pour le code
info = {
    'knobs': KNOBS, 'knobTop': KNOB_TOP, 'knobSkirt': KNOB_SKIRT,
    'mode': MODE_C, 'modeTop': MODE_TOP, 'modeSkirt': MODE_SKIRT, 'modeAngles': MODE_ANGLES,
    'led': LED, 'foot': FOOT, 'footR': 44.0,
    'glowRect': [x0 / 2, y0 / 2, RAD, RAD],
    'row': ROW, 'bar': BAR, 'display': DISPLAY, 'box': BOX,
}
json.dump(info, open(os.path.join(HERE, 'layout.json'), 'w'), indent=1)

def P(p): return '{ %.2ff, %.2ff }' % (p[0], p[1])
def R4(r): return '{ %.2ff, %.2ff, %.2ff, %.2ff }' % (r[0], r[1], r[2] - r[0], r[3] - r[1])
with open(os.path.join(ROOT, 'Layout.h'), 'w') as fo:
    fo.write('// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)\n#pragma once\n')
    fo.write('#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{\n')
    fo.write('    const juce::Point<float> ratePos %s, depthPos %s, modePos %s;\n' % (P(KNOBS['rate']), P(KNOBS['depth']), P(MODE_C)))
    fo.write('    const float knobTop = %.2ff, knobSkirt = %.2ff, modeTop = %.2ff, modeSkirt = %.2ff;\n' % (KNOB_TOP, KNOB_SKIRT, MODE_TOP, MODE_SKIRT))
    fo.write('    const float modeFirstDeg = %.4ff, modeStepDeg = %.4ff;     // 8 positions\n' % (MODE_ANGLES[0], MODE_ANGLES[1] - MODE_ANGLES[0]))
    fo.write('    const juce::Point<float> ledPos %s, footPos %s;\n' % (P(LED), P(FOOT)))
    fo.write('    const float footR = 44.0f, ledLensR = %.2ff;\n' % (LENS / 2))
    g = info['glowRect']
    fo.write('    const juce::Rectangle<float> glowRect { %.2ff, %.2ff, %.2ff, %.2ff };\n' % (g[0], g[1], g[2], g[3]))
    fo.write('    const juce::Rectangle<float> rowRect %s;\n' % R4(ROW))
    fo.write('    const juce::Rectangle<float> barRect %s;\n' % R4(BAR))
    fo.write('}\n')
print('ok', json.dumps({'glow': info['glowRect']}))
