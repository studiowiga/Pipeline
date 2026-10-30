# Pipeline (Studio Wiga)

Plugin VST3 (Windows x64 et macOS universel) au format pédale simple : **vibrato de hauteur à 8 modes**, d'après le fonctionnement de l'**EarthQuaker Devices Aqueduct**. Nom dans le DAW : **Pipeline (Studio Wiga)**.

Visuel : `design/source/pipeline_visuel_vagues.png` (fourni par Studio Wiga, vagues), retravaillé par `tools/make_background.py` (pédale moins haute, potards abaissés, LED en haut, footswitch et logo remontés, MODE au-dessus du sélecteur, cadrage serré). Footswitch d'Echoflex (vue de dessus). Toutes les positions passent par `Layout.h`.

## Commandes

| Commande | Rôle |
|---|---|
| RATE | Vitesse du LFO, 0,1 Hz à 16 Hz (≈ 1,8 Hz à midi). Env R : sensibilité de l'enveloppe. Env P : sensibilité et amplitude du bend. En synchro tempo : valeur de note (4 mesures à 1/32, pointées et triolets). |
| DEPTH | Intensité du vibrato (retard jusqu'à 22 ms, écart de hauteur tenu vers +4 / -6 demi-tons). Env D : sensibilité de l'enveloppe. Env P : mélange sec / traité (midi = 50/50). |
| MODE | Sine, Triangle, Ramp, Square, Random, Env D, Env R, Env P (clic direct possible sur l'étiquette). |
| Footswitch | Flexi-Switch : appui bref = marche / arrêt, appui maintenu (> 0,45 s, effet coupé) = momentané. Fondu de 12 ms. |

Les formes Sine / Triangle / Ramp / Square sont des formes de **hauteur** (le temps de retard en est l'intégrale) : Square donne de vrais trilles, Ramp un « ping » de sonar. Random passe du « disque voilé » (sinus) aux glissandos aléatoires quand Depth monte. Seul Env P mélange le signal sec, comme sur la pédale.

## MIDI

MIDI Learn sur toutes les commandes (clic droit), sauvegardé avec le projet. Par défaut : Rate CC 20, Depth CC 21, Mode CC 22 (8 zones), Tempo Sync CC 23, Footswitch CC 24 ; 14 bits sur CC 52-53 ; Program Change 1-15 = presets d'usine. Pédales d'expression : rampe + lissage 2 pôles, course apprise automatiquement, zones mortes.

## Anti-gel v2

JUCE 8.0.15 ; rendu logiciel forcé sous Windows (réappliqué à chaque nouvelle fenêtre hôte), aucun calcul lourd dans `paint()` (caches refaits par le timer), chien de garde de redessin (1,5 s), aucun appel à l'hôte ni recherche par chaîne dans le thread audio (file atomique vidée par un timer à 60 Hz).

## Fichiers

- `PipelineDSP.h` : moteur audio (ligne de retard modulée, interpolation Hermite, suiveur d'enveloppe, fondu de têtes de lecture).
- `PluginProcessor.*`, `PluginEditor.*`, `Layout.h` (généré), `background.jpg`, `glow_led.png`, `knob_strip.png` (potards de Holyverb), `mode_labels.png` (étiquettes allumées).
- `tools/make_background.py` : fond tiré du visuel (repères effacés, éléments déplacés), calque de la LED, `Layout.h`.
- `tools/render/` : compile la vraie fenêtre sous Linux et exporte les captures ; `tools/manual.py` : notice PDF.
- `tests/test_dsp.cpp` : banc d'essai du moteur (hauteur mesurée par mode, crêtes, bypass exact).
- `docs/Pipeline_Manual_EN-FR_v1.4.1.pdf` : notice bilingue.

## Compilation

```
cmake -B build && cmake --build build --config Release
```
Le workflow GitHub `build.yml` produit les artefacts `Pipeline-VST3-Windows` et `Pipeline-VST3-macOS`.

## Historique

- **1.4.1** : sélecteur MODE à crans (résistance, bascule avec léger rebond, butées en fin de course), étiquettes des modes agrandies et éteintes quand l'effet est coupé, nom des presets agrandi (le plus long tient entier), zone assombrie du footswitch agrandie.
- **1.4.0** : sélecteur MODE agrandi avec crans plus marqués, étiquette du mode choisi allumée en bleu (écriture LED), LED du haut agrandie (halo adouci), écran : texte à gauche et oscilloscope animé de la modulation à droite.
- **1.3.2** : footswitch d'Echoflex (vue de dessus), bulles et filet du cadre préservés, ombre carrée des potards supprimée, vagues intactes sous l'écran, fond assombri, menu clic droit sous le pointeur, footswitch MIDI : chaque appui bascule marche / arrêt (par défaut).
- **1.3.1** : ombres et cercles des anciens potards supprimés, graduations redessinées (dont ENV R / ENV P), jacks et IN / OUT au niveau du titre, footswitch remonté sans déformer les vagues, écran nettoyé.
- **1.3.0** : potards moletés et embases jack de Holyverb, potards encore abaissés, pédale élargie.
- **1.2.0** : nouveau visuel « vagues » avec les mêmes retouches (hauteur réduite, potards abaissés, LED en haut, footswitch et logo remontés, MODE au-dessus du sélecteur) ; pédale agrandie dans la fenêtre (marges réduites, taille de fenêtre inchangée).
- **1.1.0** : visuel définitif de Studio Wiga intégré et retouché (hauteur réduite, potards abaissés, LED en haut, footswitch Echoflex et logo remontés, MODE au-dessus du sélecteur).
- **1.0.0** : première version (8 modes, Flexi-Switch, synchro tempo, MIDI Learn, 15 presets, visuel provisoire).
