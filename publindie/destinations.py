# -*- coding: utf-8 -*-
"""LES VITRINES ET LEURS FORMATS — une règle, un endroit (comme `reseaux.py` pour les posts).

Une VITRINE est l'endroit où un produit se montre et se vend : la page itch.io, la page Steam, le site du studio. Chacune
a ses PIÈCES (couverture, bannière, captures, capsules, boucles vidéo) et chaque pièce ses formats : tailles, poids,
sortes de médias, nombre. `verifier_piece` dit ce qui dépasse ; `publindie vitrine` refuse un lot qu'une vitrine
refuserait.

⚠ RELEVÉ LE 19 OCTOBRE 2026. itch.io : guide de tiers (hedgiespresso.itch.io/itch-page-image-templates) et forum d'itch
(la limite de 3 Mo par image, GIF compris, confirmée par un administrateur en 2018-2020 et par des refus signalés depuis ;
un fichier trop lourd fait échouer TOUT le lot téléversé). Steam : partner.steamgames.com/doc/store/assets (captures, les
capsules agrandies d'août 2024) ; « au moins 5 captures » vient des guides de tiers. Le site : nos propres règles
(`SpannerGamesWeb/LISEZMOI.md` : WebP 960 / 1920 / 2560 ; Cloudflare Pages refuse un fichier de plus de 25 Mio).
Les limites changent : c'est ICI qu'on les change.
"""

RELEVE = "2026-10-19"

# Une pièce : sortes acceptées (image, gif, boucle), taille exacte (`taille`) ou minimale (`min`) / maximale (`max`),
# rapport largeur / hauteur (`rapport`, ± 1 %), poids maximal (`mo`), nombre (`nombre_min`, `nombre_max`, `conseil`).
DESTINATIONS = {
    "itch": {
        "nom": "itch.io",
        "pieces": {
            "couverture": {"sortes": ["image", "gif"], "min": (315, 250), "max": (3840, 2160), "rapport": 630 / 500,
                           "mo": 3, "nombre_min": 1, "nombre_max": 1,
                           "conseil": "630 × 500 : elle se voit partout (accueil, recherche, collections), en petit"},
            "banniere": {"sortes": ["image", "gif"], "min": (960, 100), "mo": 3, "nombre_max": 1,
                         "conseil": "960 px de large : la colonne de la page"},
            "capture": {"sortes": ["image", "gif"], "max": (3840, 2160), "mo": 3, "nombre_min": 3,
                        "conseil": "3 Mo PAR FICHIER, GIF compris ; 1920 × 1080 pour la visionneuse plein écran"},
        },
    },
    "steam": {
        "nom": "Steam",
        "pieces": {
            "capture": {"sortes": ["image"], "min": (1920, 1080), "rapport": 16 / 9, "nombre_min": 5,
                        "conseil": "tout public (sinon cachées à une partie des visiteurs) ; le jeu, pas du marketing"},
            "capsule_entete": {"sortes": ["image"], "taille": (920, 430), "nombre_min": 1, "nombre_max": 1},
            "capsule_petite": {"sortes": ["image"], "taille": (462, 174), "nombre_min": 1, "nombre_max": 1},
            "capsule_principale": {"sortes": ["image"], "taille": (1232, 706), "nombre_min": 1, "nombre_max": 1},
            "capsule_verticale": {"sortes": ["image"], "taille": (748, 896), "nombre_min": 1, "nombre_max": 1},
            "bibliotheque": {"sortes": ["image"], "taille": (600, 900), "nombre_min": 1, "nombre_max": 1},
        },
    },
    "site": {
        "nom": "le site du studio",
        "pieces": {
            "image": {"sortes": ["image"], "min": (1920, 1080), "conseil": "déclinée en WebP 960 / 1920 / 2560"},
            "boucle": {"sortes": ["boucle"], "min": (1280, 720), "mo": 6, "secondes_max": 12,
                       "conseil": "muette, WebM + MP4 + image d'attente ; 6 Mo au plus (Pages : 25 Mio par fichier)"},
        },
    },
}


def piece(destination, role):
    d = DESTINATIONS.get(destination)
    if d is None:
        raise KeyError("vitrine inconnue : %s (connues : %s)" % (destination, ", ".join(DESTINATIONS)))
    p = d["pieces"].get(role)
    if p is None:
        raise KeyError("%s n'a pas de pièce « %s » (seulement : %s)" % (d["nom"], role, ", ".join(d["pieces"])))
    return p


def verifier_piece(destination, role, sorte, largeur=None, hauteur=None, mo=None, secondes=None):
    """Les refus d'UN fichier pour une pièce d'une vitrine : une liste de phrases, vide si tout passe."""
    p = piece(destination, role)
    nom = "%s, %s" % (DESTINATIONS[destination]["nom"], role)
    fautes = []
    if sorte not in p["sortes"]:
        return ["%s : « %s » refusé (seulement : %s)" % (nom, sorte, ", ".join(p["sortes"]))]
    if largeur and hauteur:
        if p.get("taille") and (largeur, hauteur) != tuple(p["taille"]):
            fautes.append("%s : %d × %d, il faut exactement %d × %d" % (nom, largeur, hauteur, *p["taille"]))
        if p.get("min") and (largeur < p["min"][0] or hauteur < p["min"][1]):
            fautes.append("%s : %d × %d, au moins %d × %d" % (nom, largeur, hauteur, *p["min"]))
        if p.get("max") and (largeur > p["max"][0] or hauteur > p["max"][1]):
            fautes.append("%s : %d × %d, au plus %d × %d" % (nom, largeur, hauteur, *p["max"]))
        if p.get("rapport") and abs(largeur / hauteur - p["rapport"]) > p["rapport"] * 0.01:
            fautes.append("%s : rapport %.3f, attendu %.3f" % (nom, largeur / hauteur, p["rapport"]))
    if mo is not None and p.get("mo") and mo > p["mo"]:
        fautes.append("%s : %.2f Mo, %g au plus" % (nom, mo, p["mo"]))
    if secondes is not None and p.get("secondes_max") and secondes > p["secondes_max"] + 0.05:
        fautes.append("%s : %.1f s, %g au plus" % (nom, secondes, p["secondes_max"]))
    return fautes


def verifier_nombres(destination, comptes):
    """Les pièces trop ou pas assez nombreuses. `comptes` : {role: nombre}."""
    d = DESTINATIONS[destination]
    fautes = []
    for role, p in d["pieces"].items():
        n = comptes.get(role, 0)
        if p.get("nombre_min") and n < p["nombre_min"]:
            fautes.append("%s : %d « %s », il en faut au moins %d" % (d["nom"], n, role, p["nombre_min"]))
        if p.get("nombre_max") is not None and n > p["nombre_max"]:
            fautes.append("%s : %d « %s », %d au plus" % (d["nom"], n, role, p["nombre_max"]))
    return fautes
