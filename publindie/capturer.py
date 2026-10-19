# -*- coding: utf-8 -*-
"""CAPTURER — Godot photographie et filme les plans d'une RECETTE, à la taille exacte, sans souris.

    python -m publindie capturer RECETTE.json [--seulement NOM] [--essai]

Une recette (dans `<studio>/PROJETS/<Média>/01_scripts/recettes/<nom>.json`) :

    {
      "projet": "WaterDrop",                         # le projet Godot (clé de `projets` dans publindie.json)
      "media": "MarchingBlocks",                     # le dossier média qui reçoit (défaut : le projet)
      "scene": "res://GAME/world/world.tscn",
      "sortie": "02_rushes/vitrine/waterdrop",       # relatif au dossier média
      "taille": [1920, 1080], "fps": 30,
      "attente_depart": 150,                         # images avant le premier plan (la scène se bâtit)
      "cacher": ["TestElements"], "figer": ["TopDownCamera"],
      "cacher_interface": true,                      # le HUD du jeu (CanvasLayer, Control) n'entre pas dans l'image
      "soleil": {"noeud": "Sun", "elevation": 18, "azimut": 210, "energie": 1.1},
      "plans": [
        {"nom": "bourg", "oeil": [10, 30, 40], "cible": [0, 0, 0], "fov": 45},
        {"nom": "survol", "oeil": [...], "cible": [...], "film": {"secondes": 6, "fin_oeil": [...], "fin_cible": [...]}}
      ]
    }

Une image : `<sortie>/<nom>.png`. Un film : les PNG à pas fixe dans `<sortie>/<nom>/`, puis `<sortie>/<nom>.mp4`
(H.264 CRF 14, à la cadence de la recette) — le dossier de PNG est effacé quand le MP4 est lu.

⚠ LA CARTE GRAPHIQUE SE PARTAGE (charte de MarchingBlocks) : un tournage pendant qu'une autre session filme lui vole des
images. `capturer` dit l'occupation du GPU avant de lancer.
⚠ UNE SCÈNE, PAS L'APPLI : l'appli MarchingBlocks se filme par ses propres `DEV_TOOLS/filmer_*.gd` (ses gestes appellent
ses vrais outils) ; `capturer` photographie une SCÈNE Godot (un jeu, un exemple posé par un greffon).
"""
import json
import os
import shutil
import subprocess
import tempfile

from publindie import chemins as C

ICI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(ICI, "godot", "capturer.gd")


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        r = json.load(f)
    for cle in ("projet", "scene", "plans"):
        if cle not in r:
            raise SystemExit("recette sans « %s » : %s" % (cle, chemin))
    if r["projet"] not in C.PROJETS:
        raise SystemExit("projet inconnu : %s" % r["projet"])
    noms = [p["nom"] for p in r["plans"]]
    if len(set(noms)) != len(noms):
        raise SystemExit("deux plans portent le même nom dans %s" % chemin)
    for p in r["plans"]:
        for cle in ("oeil", "cible"):
            if len(p.get(cle, [])) != 3:
                raise SystemExit("plan %s : « %s » doit être [x, y, z]" % (p["nom"], cle))
    return r


def commande(r, sortie, recette_resolue, seulement=None):
    cmd = [C.OUTILS["godot"], "--path", C.PROJETS[r["projet"]], "--script", SCRIPT,
           "--resolution", "%dx%d" % tuple(r.get("taille", [1920, 1080]))]
    if any("film" in p for p in r["plans"]):
        cmd += ["--fixed-fps", str(r.get("fps", 30))]
    cmd += ["--", "--recette=" + recette_resolue, "--sortie=" + sortie]
    if seulement:
        cmd.append("--seulement=" + seulement)
    return cmd


def occupation_gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10)
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return None


def encoder_films(r, sortie):
    faits = []
    for p in r["plans"]:
        d = os.path.join(sortie, p["nom"])
        if "film" not in p or not os.path.isdir(d) or not os.listdir(d):
            continue
        mp4 = d + ".mp4"
        fps = p["film"].get("fps", r.get("fps", 30))
        subprocess.run([C.OUTILS["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps),
                        "-i", os.path.join(d, "%05d.png"), "-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
                        "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], check=True)
        if os.path.getsize(mp4) > 0:
            shutil.rmtree(d)
        faits.append(mp4)
    return faits


def capturer(chemin, seulement=None, essai=False):
    r = charger(chemin)
    media = r.get("media", r["projet"])
    sortie = os.path.abspath(C.dossier_projet(media, r.get("sortie", os.path.join("02_rushes", "captures"))))
    os.makedirs(sortie, exist_ok=True)
    resolue = os.path.join(tempfile.gettempdir(), "publindie_recette_%s.json" % os.path.basename(chemin)[:-5])
    with open(resolue, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False)
    cmd = commande(r, sortie, resolue, seulement)
    print(" ".join('"%s"' % c if " " in c else c for c in cmd))
    if essai:
        return 0
    g = occupation_gpu()
    if g is not None and g > 60:
        print("⚠ le GPU est déjà occupé à %d %% : une autre session tourne peut-être (images perdues, lenteur)" % g)
    journal = os.path.join(sortie, "capturer.log")
    with open(journal, "w", encoding="utf-8") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=r.get("delai_max", 1800))
    texte = open(journal, encoding="utf-8", errors="replace").read()
    images = [l.split(" ", 2)[2] for l in texte.splitlines() if l.startswith("PUBLINDIE image ")]
    for l in texte.splitlines():
        if "⚠" in l or "PUBLINDIE :" in l or "SCRIPT ERROR" in l or l.startswith("ERROR"):
            print("  " + l)
    films = encoder_films(r, sortie)
    for f in images + films:
        print("  ✓ %s" % f)
    attendus = [p["nom"] for p in r["plans"] if not seulement or p["nom"] == seulement]
    manquants = [n for n in attendus if not os.path.exists(os.path.join(sortie, n + ".png"))
                 and not os.path.exists(os.path.join(sortie, n + ".mp4"))]
    if manquants or p.returncode != 0 or "PUBLINDIE fini" not in texte:
        print("✗ Godot a rendu %d ; manquent : %s (journal : %s)" % (p.returncode, ", ".join(manquants) or "—", journal))
        return 1
    print("VERDICT : %d plan(s) — à REGARDER avant de s'en servir" % len(attendus))
    return 0
