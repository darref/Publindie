# -*- coding: utf-8 -*-
"""LA CHAÎNE YOUTUBE — bannière et avatar, tirés du logo.

    python -m publindie.chaine        # écrit CHAINE/banniere_2560x1440.png et CHAINE/avatar_800x800.png

⚠ LA BANNIÈRE N'EST VUE ENTIÈRE QUE SUR UNE TÉLÉ. YouTube la rogne selon l'écran : seule la ZONE SÛRE
centrale de 1546 × 423 se voit partout (téléphone compris). Tout ce qui doit se lire — logo, nom,
phrase — tient dedans ; le reste n'est que du fond qui prolonge.
⚠ L'AVATAR EST RONDI PAR YOUTUBE : le logo garde une marge pour que le cercle ne mange pas la clé.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from publindie import chemins as C

LARGEUR, HAUTEUR = 2560, 1440
SURE = (1546, 423)
PHRASE = "Tools and games, made by one developer"


def fond(l, h):
    """Le violet de la marque, à peine éclairci au centre : un aplat se lit comme un trou."""
    img = Image.new("RGB", (l, h), C.VIOLET)
    halo = Image.new("L", (l, h), 0)
    ImageDraw.Draw(halo).ellipse((l * 0.2, h * 0.1, l * 0.8, h * 0.9), fill=255)
    halo = halo.filter(ImageFilter.GaussianBlur(h * 0.25))
    clair = Image.new("RGB", (l, h), tuple(min(255, int(c * 1.35)) for c in C.VIOLET))
    return Image.composite(clair, img, halo)


def logo_serre(cote):
    """Le logo, détouré depuis l'original de 1024 px et recadré sur la clé, mis à `cote` px de haut.

    ⚠ `spannergames_detoure.png` ne fait que 128 px : agrandi, il était flou, et `thumbnail` ne grandit
    jamais (le logo restait minuscule, vu à l'image). On détoure donc l'original : l'alpha est la part
    d'OR de chaque pixel entre le violet du fond et l'or de la clé, sur le canal rouge, qui les sépare le
    mieux (40 contre ~214).
    """
    src = Image.open(C.MARQUE["logo"]).convert("RGB")
    r = src.getchannel("R")
    alpha = r.point(lambda v: max(0, min(255, int((v - C.VIOLET[0] - 8) * 255 / (C.OR[0] - C.VIOLET[0] - 8)))))
    logo = Image.new("RGBA", src.size, C.OR + (0,))
    logo.putalpha(alpha)
    logo = logo.crop(alpha.point(lambda v: 255 if v > 64 else 0).getbbox())
    return logo.resize((max(1, round(logo.width * cote / logo.height)), cote), Image.LANCZOS)


def banniere():
    img = fond(LARGEUR, HAUTEUR)
    d = ImageDraw.Draw(img)
    x0, y0 = (LARGEUR - SURE[0]) // 2, (HAUTEUR - SURE[1]) // 2
    logo = logo_serre(int(SURE[1] * 0.78))
    titre = ImageFont.truetype(C.POLICES["titre"], 150)
    texte = ImageFont.truetype(C.POLICES["texte"], 54)
    lt = d.textlength("SpannerGames", font=titre)
    lp = d.textlength(PHRASE, font=texte)
    bloc = logo.width + 50 + max(lt, lp)
    gx = x0 + (SURE[0] - bloc) // 2
    img.paste(logo, (int(gx), y0 + (SURE[1] - logo.height) // 2), logo)
    tx = gx + logo.width + 50
    d.text((tx, y0 + 70), "SpannerGames", font=titre, fill=C.OR)
    d.text((tx, y0 + 270), PHRASE, font=texte, fill=(225, 215, 240))
    return img


def avatar():
    img = fond(800, 800)
    logo = logo_serre(470)
    img.paste(logo, ((800 - logo.width) // 2, (800 - logo.height) // 2), logo)
    return img


if __name__ == "__main__":
    sortie = os.path.join(C.RACINE, "CHAINE")
    banniere().save(os.path.join(sortie, "banniere_2560x1440.png"))
    avatar().save(os.path.join(sortie, "avatar_800x800.png"))
    print("écrit :", sortie)
