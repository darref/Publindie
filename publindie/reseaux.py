# -*- coding: utf-8 -*-
"""LES RÉSEAUX ET LEURS LIMITES — une règle, un endroit.

Chaque réseau : la longueur des textes, le nombre de hashtags, ce qu'il accepte comme média (et son poids, sa durée, son
format). `verifier_texte` et `verifier_media` disent ce qui dépasse ; une fiche de publication (`fiches.py`) est refusée
tant qu'un réseau la refuserait.

⚠ RELEVÉ LE 18 OCTOBRE 2026, sur des guides de tiers (socialync.io, blotato.com) et la presse (Bluesky : 10 minutes et
300 Mo depuis août 2026) — PAS sur les centres d'aide des réseaux. Les limites changent souvent : à revérifier, et c'est
ICI qu'on les change. Les choix PRUDENTS sont dits (`prudent`) : on prend la plus petite des valeurs annoncées.

BLUESKY ET YOUTUBE REVÉRIFIÉS LE 21 OCTOBRE 2026 SUR LES SOURCES OFFICIELLES (Publindie y poste lui-même) :
- Bluesky, lexiques de `bluesky-social/atproto` : `app.bsky.feed.post` (texte : 300 GRAPHÈMES et 3 000 octets),
  `app.bsky.embed.images` (4 images, 2 000 000 octets chacune, texte alternatif), `app.bsky.embed.video` (MP4 seulement,
  300 000 000 octets) ; la durée (10 minutes) reste celle de la presse.
- YouTube : un Short est une vidéo de 3 minutes au plus, CARRÉE ou verticale, sans #Shorts obligatoire
  (support.google.com/youtube/answer/15424877).
"""
import re

try:                                    # `regex` sait découper en graphèmes (\X) ; sans lui, une approximation
    import regex as _regex
except ImportError:                     # pragma: no cover — le téléphone peut ne pas l'avoir
    _regex = None

RELEVE = "2026-10-18"

# texte : caractères (graphèmes pour Bluesky) ; titre : None si le réseau n'a pas de titre ; medias : les sortes
# acceptées ; video_s / video_mo / gif_mo : maxima ; vertical : la vidéo doit être en 9:16.
RESEAUX = {
    "youtube": {"nom": "YouTube", "titre": 100, "texte": 5000, "tags_car": 500, "medias": ["video"],
                "video_s": None, "video_mo": None},
    "youtube_short": {"nom": "YouTube Shorts", "titre": 100, "texte": 5000, "tags_car": 500, "medias": ["short"],
                      "video_s": 180, "vertical": True, "carre_ok": True},
    "x": {"nom": "X", "titre": None, "texte": 280, "medias": ["gif", "video", "image"], "video_s": 140,
          "video_mo": 512, "gif_mo": 15, "lien_en_reponse": True},
    "bluesky": {"nom": "Bluesky", "titre": None, "texte": 300, "texte_octets": 3000, "graphemes": True,
                "medias": ["gif", "video", "image"], "video_s": 600, "video_mo": 286.1, "gif_mo": 286.1,
                "image_mo": 1.907, "images": 4,
                "prudent": "300 000 000 octets = 286,1 Mo ; une image : 2 000 000 octets = 1,907 Mo (lexiques)"},
    "mastodon": {"nom": "Mastodon", "titre": None, "texte": 500, "medias": ["gif", "video", "image"],
                 "video_mo": 40, "gif_mo": 40, "prudent": "40 Mo : la limite dépend de l'instance"},
    "tiktok": {"nom": "TikTok", "titre": None, "texte": 2200, "medias": ["short"], "video_s": 600, "vertical": True,
               "prudent": "2 200 caractères (certains guides disent 4 000)"},
    "instagram": {"nom": "Instagram", "titre": None, "texte": 2200, "hashtags": 30, "medias": ["short", "video"],
                  "video_s": 90, "vertical": True,
                  "prudent": "90 s : la limite de l'API ; l'appli accepte des Reels plus longs"},
    "reddit": {"nom": "Reddit", "titre": 300, "texte": 40000, "medias": ["gif", "video", "image"], "video_s": 900,
               "video_mo": 1024, "une_communaute": True},
}

HASHTAG = re.compile(r"(?<!\w)#\w+")


# Ce qui se colle au graphème précédent quand `regex` manque : marques combinantes, sélecteurs de variante, teintes de
# peau, ZWJ (et le caractère qui le suit), le second indicateur régional d'un drapeau.
_COLLE = re.compile("[\u0300-\u036f\u1ab0-\u1aff\u20d0-\u20ff\ufe00-\ufe0f\U0001f3fb-\U0001f3ff\U000e0020-\U000e007f]")


def graphemes(texte):
    """Le nombre de GRAPHÈMES (ce que Bluesky compte : « 👨‍❤️‍👨 » en vaut un, pas huit)."""
    if _regex is not None:
        return len(_regex.findall(r"\X", texte))
    n, apres_zwj, drapeau = 0, False, False
    for c in texte:
        if c == "\u200d":
            apres_zwj = True
            continue
        if apres_zwj or _COLLE.match(c):
            apres_zwj = False
            continue
        if "\U0001f1e6" <= c <= "\U0001f1ff":
            drapeau = not drapeau
            if not drapeau:
                continue
        else:
            drapeau = False
        n += 1
    return n


def longueur(texte, reseau):
    """La longueur que COMPTE le réseau. Sur X, un lien vaut 23 caractères quelle que soit sa longueur ; Bluesky compte
    des graphèmes."""
    if reseau == "x":
        texte = re.sub(r"https?://\S+", "x" * 23, texte)
    if RESEAUX.get(reseau, {}).get("graphemes"):
        return graphemes(texte)
    return len(texte)


def verifier_texte(reseau, texte="", titre=None):
    """Les dépassements d'un texte (et d'un titre) pour un réseau : une liste de phrases, vide si tout passe."""
    r = RESEAUX[reseau]
    fautes = []
    n = longueur(texte or "", reseau)
    if r.get("texte") and n > r["texte"]:
        fautes.append("%s : texte de %d caractères, %d au plus" % (r["nom"], n, r["texte"]))
    if r.get("texte_octets") and len((texte or "").encode("utf-8")) > r["texte_octets"]:
        fautes.append("%s : texte de %d octets, %d au plus" % (r["nom"], len(texte.encode("utf-8")), r["texte_octets"]))
    if r.get("hashtags") and len(HASHTAG.findall(texte or "")) > r["hashtags"]:
        fautes.append("%s : %d hashtags, %d au plus" % (r["nom"], len(HASHTAG.findall(texte)), r["hashtags"]))
    if titre is not None:
        if r.get("titre") is None:
            fautes.append("%s n'a pas de titre" % r["nom"])
        elif len(titre) > r["titre"]:
            fautes.append("%s : titre de %d caractères, %d au plus" % (r["nom"], len(titre), r["titre"]))
    elif r.get("titre") is not None and reseau in ("youtube", "youtube_short", "reddit"):
        fautes.append("%s : il faut un titre" % r["nom"])
    if titre is not None and reseau in ("youtube", "youtube_short") and re.search(r"[<>]", titre):
        fautes.append("%s : un titre ne peut pas contenir < ni >" % r["nom"])
    if r.get("lien_en_reponse") and re.search(r"https?://", texte or ""):
        fautes.append("%s : le lien va en PREMIÈRE RÉPONSE (un lien dans le post coûte 30 à 50 %% de portée)" % r["nom"])
    return fautes


def verifier_media(reseau, sorte, mo=None, secondes=None, largeur=None, hauteur=None):
    """Les refus d'un média pour un réseau. `sorte` : video, short, gif, image. Les mesures absentes ne sont pas jugées."""
    r = RESEAUX[reseau]
    fautes = []
    if sorte not in r["medias"]:
        fautes.append("%s n'accepte pas « %s » (seulement : %s)" % (r["nom"], sorte, ", ".join(r["medias"])))
        return fautes
    limite_mo = {"gif": r.get("gif_mo"), "image": r.get("image_mo")}.get(sorte, r.get("video_mo"))
    if mo is not None and limite_mo and mo > limite_mo:
        fautes.append("%s : %.1f Mo, %d au plus" % (r["nom"], mo, limite_mo))
    if secondes is not None and sorte in ("video", "short") and r.get("video_s") and secondes > r["video_s"] + 0.5:
        fautes.append("%s : %.0f s, %d au plus" % (r["nom"], secondes, r["video_s"]))
    if r.get("vertical") and largeur and hauteur and sorte in ("video", "short") and (
            hauteur < largeur if r.get("carre_ok") else hauteur <= largeur):
        fautes.append("%s : la vidéo doit être verticale (9:16)%s, elle fait %d × %d" % (
            r["nom"], " ou carrée" if r.get("carre_ok") else "", largeur, hauteur))
    return fautes


def verifier_tags(reseau, tags):
    """YouTube : 500 caractères de tags au plus, comptés comme YouTube les compte (une virgule entre deux tags, des
    guillemets autour d'un tag qui contient une espace)."""
    r = RESEAUX[reseau]
    if not tags or not r.get("tags_car"):
        return []
    n = sum(len(t) + (2 if " " in t else 0) for t in tags) + len(tags) - 1
    if n > r["tags_car"]:
        return ["%s : %d caractères de tags, %d au plus" % (r["nom"], n, r["tags_car"])]
    return []
