# -*- coding: utf-8 -*-
"""LES CHEMINS DU STUDIO — un seul endroit pour dire où vivent les outils et les projets.

    python -m publindie.chemins      # dit ce qui est présent et ce qui manque

Le STUDIO est le dossier des médias (pour SpannerGames : `D:/SpannerGames`) : la variable d'environnement
`PUBLINDIE_STUDIO`, sinon le premier dossier de `STUDIOS_CONNUS` qui existe. Son `publindie.json` dit ses projets, ses
outils (si un chemin diffère des défauts), ses polices et sa marque ; ce module garde les noms d'avant (`RACINE`,
`OUTILS`, `PROJETS`, `POLICES`, `MARQUE`, `dossier_projet`) : les scripts écrits pour `SpannerGames/OUTILS` marchent tels
quels.

⚠ UNE RÈGLE, UN ENDROIT : aucun autre script ne recopie un chemin d'outil. Si Godot change de version ou si ffmpeg
déménage, c'est dans le `publindie.json` du studio (ou ici, pour le défaut) et nulle part ailleurs.
"""
import json
import os
import shutil

STUDIOS_CONNUS = ["D:/SpannerGames", "/SpannerGames"]


def _studio():
    s = os.environ.get("PUBLINDIE_STUDIO", "")
    if s:
        return s
    for d in STUDIOS_CONNUS:
        if os.path.isdir(d):
            return d
    return os.getcwd()


RACINE = _studio()
CONFIG = os.path.join(RACINE, "publindie.json")
_conf = {}
if os.path.isfile(CONFIG):
    with open(CONFIG, encoding="utf-8") as f:
        _conf = json.load(f)

OUTILS = {
    "ffmpeg": shutil.which("ffmpeg") or r"C:/Users/jorda/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build/bin/ffmpeg.exe",
    "ffprobe": shutil.which("ffprobe") or r"C:/Users/jorda/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build/bin/ffprobe.exe",
    "godot": r"C:/Users/jorda/Desktop/Godot_v4.7-stable_win64.exe/Godot_v4.7-stable_win64_console.exe",
    "blender": r"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
    "obs": r"C:/Program Files/obs-studio/bin/64bit/obs64.exe",
}
OUTILS.update(_conf.get("outils", {}))

# Les sources de chaque produit : le média se TIRE du vrai produit, jamais l'inverse.
PROJETS = dict(_conf.get("projets", {}))
PROJETS.setdefault(os.path.basename(RACINE.rstrip("/\\")) or "studio", RACINE)

POLICES = {k: os.path.join(RACINE, v) for k, v in _conf.get("polices", {
    "titre": "BIBLIOTHEQUE/polices/ArchivoBlack-Regular.ttf",
    "texte": "BIBLIOTHEQUE/polices/Inter.ttf"}).items()}

MARQUE = {k: os.path.join(RACINE, v) for k, v in _conf.get("marque", {
    "logo": "MARQUE/spannergames.png",
    "logo_detoure": "MARQUE/spannergames_detoure.png"}).items()}

# Les teintes de la marque (SpannerGames : relevées sur `spannergames.png`, fond violet, clé dorée).
VIOLET = tuple(_conf.get("teintes", {}).get("violet", (42, 26, 70)))
OR = tuple(_conf.get("teintes", {}).get("or", (202, 160, 68)))


def dossier_projet(nom, *parties):
    """Le dossier média d'un projet : <studio>/PROJETS/<nom>/<parties…>."""
    if nom not in PROJETS:
        raise KeyError("projet inconnu : %s (connus : %s)" % (nom, ", ".join(PROJETS)))
    return os.path.join(RACINE, "PROJETS", nom, *parties)


def main():
    manque = 0
    print("studio : %s (%s)" % (RACINE, "publindie.json lu" if _conf else "sans publindie.json"))
    for nom, chemin in {**OUTILS, **POLICES, **MARQUE}.items():
        ok = chemin and os.path.exists(chemin)
        manque += 0 if ok else 1
        print("%-13s %s  %s" % (nom, "ok  " if ok else "MANQUE", chemin))
    for nom, chemin in PROJETS.items():
        ok = os.path.isdir(chemin)
        manque += 0 if ok else 1
        print("%-13s %s  %s" % (nom, "ok  " if ok else "MANQUE", chemin))
    return 1 if manque else 0


if __name__ == "__main__":
    raise SystemExit(main())
