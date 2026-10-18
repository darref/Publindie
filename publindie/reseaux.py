# -*- coding: utf-8 -*-
"""LES RÉSEAUX ET LEURS LIMITES — une règle, un endroit.

Chaque réseau : la longueur des textes, le nombre de hashtags, ce qu'il accepte comme média (et son poids, sa durée, son
format). `verifier_texte` et `verifier_media` disent ce qui dépasse ; une fiche de publication (`fiches.py`) est refusée
tant qu'un réseau la refuserait.

⚠ RELEVÉ LE 18 OCTOBRE 2026, sur des guides de tiers (socialync.io, blotato.com) et la presse (Bluesky : 10 minutes et
300 Mo depuis août 2026) — PAS sur les centres d'aide des réseaux. Les limites changent souvent : à revérifier, et c'est
ICI qu'on les change. Les choix PRUDENTS sont dits (`prudent`) : on prend la plus petite des valeurs annoncées.
"""
import re

RELEVE = "2026-10-18"

# texte : caractères (graphèmes pour Bluesky) ; titre : None si le réseau n'a pas de titre ; medias : les sortes
# acceptées ; video_s / video_mo / gif_mo : maxima ; vertical : la vidéo doit être en 9:16.
RESEAUX = {
    "youtube": {"nom": "YouTube", "titre": 100, "texte": 5000, "tags_car": 500, "medias": ["video"],
                "video_s": None, "video_mo": None},
    "youtube_short": {"nom": "YouTube Shorts", "titre": 100, "texte": 5000, "medias": ["short"], "video_s": 180,
                      "vertical": True},
    "x": {"nom": "X", "titre": None, "texte": 280, "medias": ["gif", "video", "image"], "video_s": 140,
          "video_mo": 512, "gif_mo": 15, "lien_en_reponse": True},
    "bluesky": {"nom": "Bluesky", "titre": None, "texte": 300, "medias": ["gif", "video", "image"], "video_s": 600,
                "video_mo": 300, "gif_mo": 300},
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


def longueur(texte, reseau):
    """La longueur que COMPTE le réseau. Sur X, un lien vaut 23 caractères quelle que soit sa longueur."""
    if reseau == "x":
        texte = re.sub(r"https?://\S+", "x" * 23, texte)
    return len(texte)


def verifier_texte(reseau, texte="", titre=None):
    """Les dépassements d'un texte (et d'un titre) pour un réseau : une liste de phrases, vide si tout passe."""
    r = RESEAUX[reseau]
    fautes = []
    n = longueur(texte or "", reseau)
    if r.get("texte") and n > r["texte"]:
        fautes.append("%s : texte de %d caractères, %d au plus" % (r["nom"], n, r["texte"]))
    if r.get("hashtags") and len(HASHTAG.findall(texte or "")) > r["hashtags"]:
        fautes.append("%s : %d hashtags, %d au plus" % (r["nom"], len(HASHTAG.findall(texte)), r["hashtags"]))
    if titre is not None:
        if r.get("titre") is None:
            fautes.append("%s n'a pas de titre" % r["nom"])
        elif len(titre) > r["titre"]:
            fautes.append("%s : titre de %d caractères, %d au plus" % (r["nom"], len(titre), r["titre"]))
    elif r.get("titre") is not None and reseau in ("youtube", "youtube_short", "reddit"):
        fautes.append("%s : il faut un titre" % r["nom"])
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
    limite_mo = r.get("gif_mo") if sorte == "gif" else r.get("video_mo")
    if mo is not None and limite_mo and mo > limite_mo:
        fautes.append("%s : %.1f Mo, %d au plus" % (r["nom"], mo, limite_mo))
    if secondes is not None and sorte in ("video", "short") and r.get("video_s") and secondes > r["video_s"] + 0.5:
        fautes.append("%s : %.0f s, %d au plus" % (r["nom"], secondes, r["video_s"]))
    if r.get("vertical") and largeur and hauteur and sorte in ("video", "short") and hauteur <= largeur:
        fautes.append("%s : la vidéo doit être verticale (9:16), elle fait %d × %d" % (r["nom"], largeur, hauteur))
    return fautes
