# -*- coding: utf-8 -*-
"""LES MINIATURES YOUTUBE — une vraie image du produit, trois à cinq mots, rien d'autre.

    python -m publindie.miniature IMAGE SORTIE.png --titre "THE RIVER DECIDES" [--teinte 40,160,220]
                               [--icone ICONE.png] [--cadre 0.5,0.5] [--cote gauche|droite]

⚠ LA MINIATURE SE LIT À 168 × 94 PIXELS (la colonne « à suivre » sur un téléphone) : au-delà de cinq
mots, le texte devient une texture. On vérifie donc AUSSI la vignette réduite (`*_petite.png`), à
l'œil, avant de publier.
⚠ L'IMAGE EST UNE CAPTURE DU VRAI PRODUIT. Une miniature retouchée ou générée qui montre ce que le
produit ne fait pas se paie en avis et en désabonnements — c'est la ligne de toute la stratégie :
le trailer vient du vrai produit, pas d'images arrangées.
⚠ YOUTUBE REFUSE AU-DELÀ DE 2 Mo : on écrit en PNG, et on repasse en JPEG qualité 92 si besoin.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from publindie import chemins as C

L, H = 1280, 720
MAX_OCTETS = 2 * 1024 * 1024


def cadrer(img, cx, cy):
    """Remplit 1280 × 720 en rognant ce qui dépasse, centré sur (cx, cy) en fractions de l'image."""
    echelle = max(L / img.width, H / img.height)
    img = img.resize((round(img.width * echelle), round(img.height * echelle)), Image.LANCZOS)
    x = min(max(0, round(img.width * cx - L / 2)), img.width - L)
    y = min(max(0, round(img.height * cy - H / 2)), img.height - H)
    return img.crop((x, y, x + L, y + H))


def ecrire_titre(img, titre, teinte, cote):
    """Le titre en capitales, sur deux lignes au plus, côté choisi, avec une ombre portée floue
    (lisible sur n'importe quel fond, sans bandeau qui cache l'image)."""
    mots = titre.upper().split()
    if len(mots) > 5:
        raise SystemExit("titre de %d mots : cinq au plus, une miniature se lit à 168 px" % len(mots))
    lignes = [" ".join(mots)] if len(mots) <= 2 else [" ".join(mots[:(len(mots) + 1) // 2]),
                                                       " ".join(mots[(len(mots) + 1) // 2:])]
    taille = 150
    police = ImageFont.truetype(C.POLICES["titre"], taille)
    mesure = ImageDraw.Draw(img)
    while max(mesure.textlength(l, font=police) for l in lignes) > L * 0.56 and taille > 60:
        taille -= 6
        police = ImageFont.truetype(C.POLICES["titre"], taille)
    marge = 56
    y = H - marge - len(lignes) * taille * 1.05
    ombre = Image.new("L", (L, H), 0)
    d_ombre = ImageDraw.Draw(ombre)
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    for i, ligne in enumerate(lignes):
        largeur = d.textlength(ligne, font=police)
        x = marge if cote == "gauche" else L - marge - largeur
        yy = y + i * taille * 1.05
        d_ombre.text((x + 6, yy + 8), ligne, font=police, fill=255)
        couleur = teinte if i == len(lignes) - 1 else (255, 255, 255)
        d.text((x, yy), ligne, font=police, fill=couleur + (255,), stroke_width=4, stroke_fill=(15, 10, 25, 255))
    ombre = ombre.filter(ImageFilter.GaussianBlur(14))
    img = Image.composite(Image.new("RGB", (L, H), (0, 0, 0)), img, ombre.point(lambda v: int(v * 0.75)))
    img.paste(calque, (0, 0), calque)
    return img


def poser_icone(img, icone, cote):
    ic = Image.open(icone).convert("RGBA")
    ic.thumbnail((150, 150), Image.LANCZOS)
    x = L - 40 - ic.width if cote == "gauche" else 40
    img.paste(ic, (x, 40), ic)
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("image"); p.add_argument("sortie")
    p.add_argument("--titre", required=True)
    p.add_argument("--teinte", default="%d,%d,%d" % C.OR)
    p.add_argument("--icone")
    p.add_argument("--cadre", default="0.5,0.5")
    p.add_argument("--cote", choices=["gauche", "droite"], default="gauche")
    a = p.parse_args()
    teinte = tuple(int(v) for v in a.teinte.split(","))
    cx, cy = (float(v) for v in a.cadre.split(","))
    img = cadrer(Image.open(a.image).convert("RGB"), cx, cy)
    img = ecrire_titre(img, a.titre, teinte, a.cote)
    if a.icone:
        img = poser_icone(img, a.icone, a.cote)
    img.save(a.sortie, optimize=True)
    if os.path.getsize(a.sortie) > MAX_OCTETS:
        a.sortie = os.path.splitext(a.sortie)[0] + ".jpg"
        img.save(a.sortie, quality=92)
    petite = os.path.splitext(a.sortie)[0] + "_petite.png"
    img.resize((168, 94), Image.LANCZOS).save(petite)
    print("miniature : %s (%d Ko) ; à juger aussi en petit : %s" % (a.sortie, os.path.getsize(a.sortie) // 1024, petite))


if __name__ == "__main__":
    main()
