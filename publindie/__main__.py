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
    python -m publindie destinations                 # les formats de chaque vitrine (itch, Steam, le site)
    python -m publindie vitrine NOM DEST [--seulement PIECE]   # le lot d'une vitrine, vérifié, et sa planche
    python -m publindie capturer RECETTE.json        # Godot photographie / filme les plans d'une recette
    python -m publindie aligner [--etapes …] [--commiter NOM…] [--forcer NOM…] [--essai]   # l'alignement (sur le PC)

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
from publindie import destinations as DS


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


def cmd_destinations(a):
    print("relevé le %s (à revérifier)" % DS.RELEVE)
    for k, d in DS.DESTINATIONS.items():
        print("== %s (%s)" % (d["nom"], k))
        for role, p in d["pieces"].items():
            bits = ["/".join(p["sortes"])]
            for cle, nom in (("taille", "exactement"), ("min", "au moins"), ("max", "au plus")):
                if p.get(cle):
                    bits.append("%s %d × %d" % (nom, *p[cle]))
            if p.get("mo"):
                bits.append("%g Mo" % p["mo"])
            if p.get("nombre_min"):
                bits.append("≥ %d" % p["nombre_min"])
            print("  %-19s %s%s" % (role, ", ".join(bits), ("  — " + p["conseil"]) if p.get("conseil") else ""))
    return 0


def cmd_vitrine(a):
    from publindie import vitrine as V
    rapport, fautes = V.fabriquer(a.nom, a.destination, a.seulement, a.planche_seule)
    for ligne in rapport:
        print("%s %-22s %-11s %s" % ("✓" if not ligne["fautes"] else "✗", ligne["nom"], ligne["role"],
                                     "  ".join("%s (%d×%d, %.2f Mo)" % (f["fichier"].rsplit("/", 1)[-1], f["largeur"],
                                                                         f["hauteur"], f["mo"])
                                               for f in ligne["fichiers"])))
        for n in ligne["notes"]:
            print("    · %s" % n)
    for x in fautes:
        print("  ✗ %s" % x)
    print("planche : %s" % C.dossier_projet(a.nom, V.charger(a.nom, a.destination)["sortie"], "planche.png"))
    print("VERDICT : %s" % ("OK — à JUGER sur la planche avant de téléverser" if not fautes else
                            "%d faute(s)" % len(fautes)))
    return 1 if fautes else 0


def cmd_capturer(a):
    from publindie import capturer as K
    return K.capturer(a.recette, a.seulement, a.essai)


def cmd_aligner(a):
    from publindie import alignement as AL
    etapes = tuple(x.strip() for x in a.etapes.split(","))
    return AL.aligner(etapes, a.commiter or (), a.forcer or (), a.essai, a.seulement or ())


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
    sp.add_parser("destinations").set_defaults(f=cmd_destinations)
    c = sp.add_parser("vitrine"); c.add_argument("nom"); c.add_argument("destination")
    c.add_argument("--seulement"); c.add_argument("--planche-seule", action="store_true",
                                                  help="ne refait rien : revérifie le lot et redessine la planche")
    c.set_defaults(f=cmd_vitrine)
    c = sp.add_parser("capturer"); c.add_argument("recette"); c.add_argument("--seulement")
    c.add_argument("--essai", action="store_true", help="écrit la commande Godot sans la lancer")
    c.set_defaults(f=cmd_capturer)
    c = sp.add_parser("aligner"); c.add_argument("--etapes", default="pousser,exporter,publindie,site")
    c.add_argument("--commiter", nargs="*"); c.add_argument("--forcer", nargs="*")
    c.add_argument("--seulement", nargs="*", help="n'exporter que ces projets")
    c.add_argument("--essai", action="store_true"); c.set_defaults(f=cmd_aligner)
    a = ap.parse_args(argv)
    return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
