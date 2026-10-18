# -*- coding: utf-8 -*-
"""PUBLINDIE — la ligne de commande.

    python -m publindie chemins                      # le studio, ses outils, ses projets : présents ou non
    python -m publindie projet NOM                   # crée l'arbre d'un projet (rien n'est écrasé)
    python -m publindie ranger [NOM]                 # ce qui est où, ce qui traîne, les exports sans fiche
    python -m publindie verifier [NOM]               # chaque fiche contre les limites de chaque réseau (rend 1 sinon)
    python -m publindie preparer NOM [ID]            # 07_publication/a_poster/<id>.md : quoi joindre, quoi coller
    python -m publindie marquer NOM ID RESEAU [URL]  # note qu'une publication est partie
    python -m publindie calendrier [--jours 14]      # ce qui est prévu, jour par jour, tous projets
    python -m publindie reseaux                      # les limites relevées de chaque réseau

Les outils de fabrication restent des modules : `python -m publindie.video …`, `.miniature`, `.voix`, `.capture`,
`.chaine` (les mêmes qu'avant dans `SpannerGames/OUTILS`).
"""
import argparse
import datetime
import sys

from publindie import chemins as C
from publindie import fiches as FI
from publindie import rangement as RG
from publindie import reseaux as R


def _projets(nom):
    if nom:
        return [nom]
    return list(C.PROJETS)


def cmd_ranger(a):
    for p in _projets(a.nom):
        r = RG.rapport(p)
        print("== %s" % p)
        if r.get("absent"):
            print("  (pas de dossier média)")
            continue
        for d, (n, o) in r["dossiers"].items():
            print("  %-15s %6d fichiers %10.0f Mo" % (d, n, o / 1048576.0))
        for h in r["hors_arbre"]:
            print("  ⚠ hors de l'arbre : %s" % h)
        for c in r["cites_absents"]:
            print("  ⚠ cité par une fiche, absent : %s" % c)
        if r["orphelins"]:
            print("  %d export(s) sans fiche :" % len(r["orphelins"]))
            for o in r["orphelins"][: a.max]:
                print("    - %s" % o)
            if len(r["orphelins"]) > a.max:
                print("    … et %d autres (--max)" % (len(r["orphelins"]) - a.max))
    return 0


def cmd_verifier(a):
    mauvais = 0
    for p in _projets(a.nom):
        for f in FI.charger_fiches(p):
            fautes = FI.verifier(f, not a.sans_mesure)
            print("%s %s/%s" % ("✓" if not fautes else "✗", p, f["id"]))
            for x in fautes:
                print("    - %s" % x)
            mauvais += bool(fautes)
    print("VERDICT : %s" % ("OK" if not mauvais else "%d fiche(s) à corriger" % mauvais))
    return 1 if mauvais else 0


def cmd_preparer(a):
    for f in FI.charger_fiches(a.nom):
        if a.id and f["id"] != a.id:
            continue
        chemin, fautes = FI.preparer(f)
        print("%s %s%s" % ("✓" if not fautes else "⚠", chemin.replace("\\", "/"),
                           "" if not fautes else " (%d faute(s), dites en tête)" % len(fautes)))
    return 0


def cmd_marquer(a):
    FI.marquer(a.nom, a.id, a.reseau, a.url or "")
    print("noté : %s/%s sur %s" % (a.nom, a.id, R.RESEAUX[a.reseau]["nom"]))
    return 0


def cmd_calendrier(a):
    depuis = datetime.date.fromisoformat(a.depuis) if a.depuis else None
    cal = FI.calendrier(_projets(None), depuis, a.jours)
    if not cal:
        print("rien de prévu (le champ « prevu » des fiches)")
    for d, items in cal.items():
        print(d.strftime("%a %d %b"))
        for projet, ident, reseau, fait in items:
            print("  %s %-14s %s/%s" % ("✓" if fait else "·", R.RESEAUX[reseau]["nom"], projet, ident))
    return 0


def cmd_reseaux(a):
    print("relevé le %s (à revérifier sur les centres d'aide)" % R.RELEVE)
    for k, r in R.RESEAUX.items():
        bits = ["texte %s" % r.get("texte")]
        for cle, nom in (("titre", "titre"), ("hashtags", "hashtags"), ("video_s", "vidéo s"), ("video_mo", "vidéo Mo"),
                         ("gif_mo", "GIF Mo")):
            if r.get(cle):
                bits.append("%s %s" % (nom, r[cle]))
        print("  %-14s %s%s" % (k, ", ".join(bits), ("  (%s)" % r["prudent"]) if r.get("prudent") else ""))
    return 0


def main(argv=None):
    # ⚠ LA CONSOLE DE WINDOWS EST EN cp1252 : les coches (✓ ✗ ⚠) y levaient une erreur d'encodage (vu sur le PC).
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="publindie", description="Les outils de publication d'un studio indé.")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("chemins").set_defaults(f=lambda a: C.main())
    c = sp.add_parser("projet"); c.add_argument("nom")
    c.set_defaults(f=lambda a: print("créés : %s" % (", ".join(RG.init(a.nom)) or "rien (tout existait)")) or 0)
    c = sp.add_parser("ranger"); c.add_argument("nom", nargs="?"); c.add_argument("--max", type=int, default=25)
    c.set_defaults(f=cmd_ranger)
    c = sp.add_parser("verifier"); c.add_argument("nom", nargs="?"); c.add_argument("--sans-mesure", action="store_true")
    c.set_defaults(f=cmd_verifier)
    c = sp.add_parser("preparer"); c.add_argument("nom"); c.add_argument("id", nargs="?"); c.set_defaults(f=cmd_preparer)
    c = sp.add_parser("marquer"); c.add_argument("nom"); c.add_argument("id"); c.add_argument("reseau")
    c.add_argument("url", nargs="?"); c.set_defaults(f=cmd_marquer)
    c = sp.add_parser("calendrier"); c.add_argument("--jours", type=int, default=14); c.add_argument("--depuis")
    c.set_defaults(f=cmd_calendrier)
    sp.add_parser("reseaux").set_defaults(f=cmd_reseaux)
    a = ap.parse_args(argv)
    return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
