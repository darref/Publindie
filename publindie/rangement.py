# -*- coding: utf-8 -*-
"""LE RANGEMENT D'UN PROJET — où vont les sources, les intermédiaires et les exports, et ce qui traîne ailleurs.

L'ARBRE DE CHAQUE PROJET (`<studio>/PROJETS/<Projet>/`) — celui de SpannerGames depuis le 4 octobre 2026, écrit une fois :
"""
import os

from publindie import chemins as C
from publindie import fiches as FI

ARBRE = {
    "01_scripts": "les scripts de tournage et de montage du projet (dans git)",
    "02_rushes": "les SOURCES brutes : ce que le produit a filmé, OBS (hors git : lourd, refaisable)",
    "03_montage": "les intermédiaires et les listes de plans (seules les listes .txt vont dans git)",
    "04_exports": "ce qui PART : la vidéo à la racine, shorts/, gif/, images/, demo/ (hors git)",
    "05_miniatures": "les miniatures YouTube et leurs vignettes",
    "06_boutique": "les pages de boutique (Steam, itch.io) : textes et captures",
    "07_publication": "fiches/ (une par publication), a_poster/ (les feuilles de route), journal.json (ce qui est parti)",
}
SOUS_EXPORTS = ["shorts", "gif", "images", "demo"]
MEDIAS = (".mp4", ".mov", ".mkv", ".webm", ".gif", ".png", ".jpg", ".jpeg", ".webp", ".zip")

__doc__ += "\n".join("    %-15s %s" % (k, v) for k, v in ARBRE.items())


def init(projet):
    """Crée l'arbre d'un projet (rien n'est écrasé). Rend les dossiers créés."""
    crees = []
    for d in list(ARBRE) + ["04_exports/" + s for s in SOUS_EXPORTS] + ["07_publication/fiches", "07_publication/a_poster"]:
        p = C.dossier_projet(projet, d)
        if not os.path.isdir(p):
            os.makedirs(p)
            crees.append(d)
    return crees


def _taille(d):
    n, o = 0, 0
    for racine, _, fichiers in os.walk(d):
        for f in fichiers:
            n += 1
            try:
                o += os.path.getsize(os.path.join(racine, f))
            except OSError:
                pass
    return n, o


def rapport(projet):
    """Ce qu'il y a dans chaque dossier, ce qui est hors de l'arbre, et les EXPORTS qu'aucune fiche ne cite (orphelins :
    préparés mais jamais planifiés). Rend un dict ; n'écrit ni ne déplace rien."""
    racine = C.dossier_projet(projet)
    sortie = {"projet": projet, "dossiers": {}, "hors_arbre": [], "orphelins": [], "cites_absents": []}
    if not os.path.isdir(racine):
        sortie["absent"] = True
        return sortie
    for e in sorted(os.listdir(racine)):
        p = os.path.join(racine, e)
        if os.path.isdir(p):
            if e in ARBRE:
                sortie["dossiers"][e] = _taille(p)
            elif not e.startswith((".", "__")):
                sortie["hors_arbre"].append(e + "/")
        elif not e.upper().startswith(("CLAUDE", "LISEZMOI", "README")):
            sortie["hors_arbre"].append(e)
    cites = set()
    for f in FI.charger_fiches(projet):
        for rel in f.get("medias", {}).values():
            cites.add(os.path.normpath(rel))
            if not os.path.isfile(os.path.join(racine, rel)):
                sortie["cites_absents"].append("%s : %s" % (f["id"], rel))
    exports = os.path.join(racine, "04_exports")
    for r, _, fs in os.walk(exports):
        for f in fs:
            if f.lower().endswith(MEDIAS):
                rel = os.path.normpath(os.path.relpath(os.path.join(r, f), racine))
                if rel not in cites:
                    sortie["orphelins"].append(rel.replace("\\", "/"))
    sortie["orphelins"].sort()
    return sortie
