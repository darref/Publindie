# -*- coding: utf-8 -*-
"""POSTER — Publindie publie lui-même sur Bluesky et YouTube (Jordan, 21 octobre 2026 : « Les deux »).

    python -m publindie poster PROJET ID [--reseau bluesky|youtube|youtube_short]            # ESSAI : rien ne part
    python -m publindie poster PROJET ID [--reseau …] --pour-de-vrai                         # le post part

⚠ L'ESSAI EST LE DÉFAUT, TOUJOURS : sans `--pour-de-vrai`, rien n'est envoyé ni ouvert (pas même une session), et le
plan dit EXACTEMENT ce qui partirait : réseau, compte, fichiers, textes, facettes, visibilité, quota.

Les refus, AVANT tout appel réseau :
- `verifier` trouve une faute dans la fiche (n'importe laquelle : une fiche fausse ne part nulle part) ;
- le journal dit que cette publication est DÉJÀ partie sur ce réseau ;
- ce que le réseau exige en plus (un texte alternatif pour chaque image, un MP4 pour une vidéo Bluesky) ;
- le secret manque (code 2, avec le mode d'emploi : ce que Jordan crée, où il le dépose).
Le journal s'écrit DÈS que le post est en ligne, avant la miniature, la playlist ou la réponse : un plantage ensuite ne
fait jamais partir la même vidéo deux fois.

Les autres réseaux restent MANUELS (`preparer`, puis `marquer`) : X fait payer son API, TikTok et Instagram exigent une
application validée.
"""
import os
import shutil
import subprocess
import tempfile

from publindie import chemins as C
from publindie import fiches as FI
from publindie import reseaux as R

AUTOMATIQUES = ("bluesky", "youtube", "youtube_short")
OK, REFUS, SECRET = 0, 1, 2


def _mime_image(chemin):
    ext = os.path.splitext(chemin)[1].lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "")


def _dimensions(chemin, sorte):
    if sorte == "image":
        try:
            from PIL import Image
            with Image.open(chemin) as im:
                return im.size
        except Exception:
            return None, None
    _, _, w, h = FI.mesurer(chemin)
    return w, h


def reseaux_vises(fiche, reseau=None):
    """Les réseaux automatiques de la fiche ; `--reseau youtube` vise aussi un `youtube_short` s'il est seul."""
    presents = [r for r in AUTOMATIQUES if r in fiche.get("reseaux", {})]
    if reseau is None:
        return presents
    if reseau == "youtube" and "youtube" not in presents and "youtube_short" in presents:
        return ["youtube_short"]
    return [reseau] if reseau in presents else []


# ---------------------------------------------------------------- le plan (ce qui partirait)

def plan(fiche, reseau):
    """Ce qui partirait sur un réseau : {"fautes": [...], "lignes": [...], ...}. Aucun appel réseau ici."""
    projet = fiche["projet"]
    t = FI.textes(fiche, reseau)
    p = {"reseau": reseau, "textes": t, "fautes": [], "lignes": [], "medias": []}
    fait = FI.charger_journal(projet).get(fiche["id"], {}).get(reseau)
    if fait:
        p["fautes"].append("DÉJÀ PARTI sur %s le %s : %s (le journal fait foi ; pour reposter, retirer la ligne du "
                           "journal à la main)" % (R.RESEAUX[reseau]["nom"], fait.get("date"), fait.get("url", "")))
    cles = t.get("media")
    cles = cles if isinstance(cles, list) else ([cles] if cles else [])
    alts = t.get("alt")
    alts = alts if isinstance(alts, list) else [alts] * len(cles)
    for i, cle in enumerate(cles):
        rel = fiche.get("medias", {}).get(cle)
        if rel is None:
            continue                                          # `verifier` l'a déjà dit
        chemin = C.dossier_projet(projet, rel)
        sorte = FI.sorte_du_media(cle, rel)
        m = {"cle": cle, "chemin": chemin, "sorte": sorte, "alt": alts[i] if i < len(alts) else None}
        if os.path.isfile(chemin):
            m["octets"] = os.path.getsize(chemin)
            m["largeur"], m["hauteur"] = _dimensions(chemin, sorte)
        p["medias"].append(m)
    nom = R.RESEAUX[reseau]["nom"]
    p["lignes"].append("== %s — %s/%s" % (nom, projet, fiche["id"]))
    for m in p["medias"]:
        p["lignes"].append("  fichier : %s (%s, %s, %s)" % (
            m["chemin"].replace("\\", "/"), m["sorte"],
            "%.2f Mo" % (m["octets"] / 1048576.0) if "octets" in m else "absent",
            "%s × %s" % (m.get("largeur"), m.get("hauteur")) if m.get("largeur") else "dimensions inconnues"))
    if reseau == "bluesky":
        _plan_bluesky(p, t)
    else:
        _plan_youtube(p, t, fiche, reseau)
    return p


def _plan_bluesky(p, t):
    from publindie import bluesky as B
    texte = t.get("texte", "")
    p["lignes"] += ["  texte (%d graphèmes, %d octets) :" % (R.graphemes(texte), len(texte.encode("utf-8")))] + [
        "    | " + l for l in texte.split("\n")]
    for f in B.facettes(texte):
        feat = f["features"][0]
        p["lignes"].append("  facette %s [%d:%d] %s" % (feat["$type"].rsplit("#", 1)[1], f["index"]["byteStart"],
                                                         f["index"]["byteEnd"], feat.get("uri") or "#" + feat["tag"]))
    p["lignes"].append("  langue : %s" % ", ".join(t.get("langs", ["en"])))
    for m in p["medias"]:
        if m["sorte"] in ("image", "gif") and not (m["alt"] or "").strip():
            p["fautes"].append("Bluesky : le média « %s » n'a pas de texte alternatif (« alt » dans la fiche)" % m["cle"])
        if m["sorte"] == "image" and not _mime_image(m["chemin"]):
            p["fautes"].append("Bluesky : image « %s » ni PNG, ni JPEG, ni WebP" % m["cle"])
        if m["sorte"] in ("video", "short") and not m["chemin"].lower().endswith(".mp4"):
            p["fautes"].append("Bluesky : une vidéo part en MP4 seulement (« %s »)" % m["cle"])
        if m["sorte"] == "gif":
            p["lignes"].append("  le GIF part en MP4 muet (converti par ffmpeg), présenté comme un GIF")
        if m["alt"]:
            p["lignes"].append("  texte alternatif (%s) : %s" % (m["cle"], m["alt"]))
    if any(m["sorte"] in ("video", "short", "gif") for m in p["medias"]):
        p["lignes"].append("  vidéo : video.bsky.app (getServiceAuth → uploadVideo → getJobStatus), quota du jour "
                           "demandé avant (getUploadLimits)")
    if t.get("premiere_reponse"):
        p["lignes"].append("  puis en réponse : %s" % t["premiere_reponse"])
        fautes = R.verifier_texte("bluesky", t["premiere_reponse"])
        p["fautes"] += ["réponse : " + f for f in fautes]


def _plan_youtube(p, t, fiche, reseau):
    from publindie import youtube as Y
    short = reseau == "youtube_short"
    c = Y.corps(t, short)
    p["corps"] = c
    p["lignes"] += ["  titre : %s" % c["snippet"]["title"],
                    "  description :"] + ["    | " + l for l in c["snippet"]["description"].split("\n")]
    p["lignes"] += ["  tags : %s" % (", ".join(c["snippet"].get("tags", [])) or "(aucun)"),
                    "  catégorie : %s ; langue : %s ; pour enfants : %s ; contenu synthétique déclaré : %s" % (
                        c["snippet"]["categoryId"], c["snippet"]["defaultLanguage"],
                        c["status"]["selfDeclaredMadeForKids"], c["status"]["containsSyntheticMedia"]),
                    "  visibilité demandée : %s%s ; abonnés prévenus : %s" % (
                        c["status"]["privacyStatus"], " (publication le %s)" % c["status"]["publishAt"]
                        if c["status"].get("publishAt") else "", t.get("notifier", True)),
                    "  ⚠ visibilité : la doc dit (15 oct. 2026) qu'un projet Google NON AUDITÉ n'est plus verrouillé "
                    "en privé ; la règle de 2020 disait l'inverse. Publindie compare ce que YouTube rend et le dit."]
    if short:
        p["lignes"].append("  Short : YouTube le classe seul (3 min au plus, carré ou vertical ; #Shorts facultatif)")
    if p["medias"] and p["medias"][0]["sorte"] not in ("video", "short"):
        p["fautes"].append("%s : le média doit être une vidéo" % R.RESEAUX[reseau]["nom"])
    cle_min = t.get("miniature")
    if cle_min:
        rel = fiche.get("medias", {}).get(cle_min)
        chemin = C.dossier_projet(fiche["projet"], rel) if rel else None
        if not chemin or not os.path.isfile(chemin):
            p["fautes"].append("YouTube : la miniature « %s » est absente" % cle_min)
        elif not chemin.lower().endswith((".png", ".jpg", ".jpeg")):
            p["fautes"].append("YouTube : la miniature est un PNG ou un JPEG")
        else:
            p["miniature"] = chemin
            p["lignes"].append("  miniature : %s (thumbnails.set, %s ; chaîne vérifiée par téléphone exigée)" % (
                chemin.replace("\\", "/"), Y.COUT["thumbnails.set"]))
    if t.get("playlist"):
        p["lignes"].append("  playlist : %s (%s)" % (t["playlist"], Y.COUT["playlistItems.insert"]))
    p["lignes"].append("  quota : videos.insert = %s" % Y.COUT["videos.insert"])


# ---------------------------------------------------------------- l'envoi

def _gif_en_mp4(chemin, dossier):
    sortie = os.path.join(dossier, os.path.splitext(os.path.basename(chemin))[0] + ".mp4")
    ffmpeg = C.OUTILS.get("ffmpeg") or "ffmpeg"
    subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", chemin, "-movflags", "+faststart", "-an",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "20",
                    sortie], check=True)
    return sortie


def _envoyer_bluesky(fiche, p, sortie, client=None):
    from publindie import bluesky as B
    t = p["textes"]
    if client is None:
        client = B.Client(B.charger_secret(C.SECRETS, fiche["projet"]))
    client.ouvrir()
    sortie("  session : %s (%s)" % (client.session.get("handle"), client.pds))
    embed, temp = None, None
    try:
        images = [m for m in p["medias"] if m["sorte"] == "image"]
        videos = [m for m in p["medias"] if m["sorte"] in ("video", "short", "gif")]
        if images:
            embed = {"$type": "app.bsky.embed.images", "images": []}
            for m in images:
                im = {"image": client.envoyer_image(m["chemin"], _mime_image(m["chemin"])), "alt": m["alt"] or ""}
                if m.get("largeur"):
                    im["aspectRatio"] = {"width": m["largeur"], "height": m["hauteur"]}
                embed["images"].append(im)
        elif videos:
            m = videos[0]
            chemin, w, h = m["chemin"], m.get("largeur"), m.get("hauteur")
            if m["sorte"] == "gif":
                temp = tempfile.mkdtemp(prefix="publindie_gif_")
                chemin = _gif_en_mp4(chemin, temp)
                w, h = _dimensions(chemin, "video")
            embed = {"$type": "app.bsky.embed.video", "video": client.envoyer_video(chemin, sortie)}
            if w and h:
                embed["aspectRatio"] = {"width": w, "height": h}
            if m["alt"]:
                embed["alt"] = m["alt"]
            if m["sorte"] == "gif":
                embed["presentation"] = "gif"
    finally:
        if temp:
            shutil.rmtree(temp, ignore_errors=True)
    r = client.poster(t.get("texte", ""), embed, t.get("langs", ["en"]))
    url = client.url_du_post(r["uri"])
    FI.marquer(fiche["projet"], fiche["id"], "bluesky", url, uri=r["uri"], par="publindie")
    sortie("  ✓ EN LIGNE : %s (journal écrit)" % url)
    if t.get("premiere_reponse"):
        try:
            rr = client.poster(t["premiere_reponse"], None, t.get("langs", ["en"]),
                               reponse_a={"uri": r["uri"], "cid": r["cid"]})
            sortie("  ✓ réponse : %s" % client.url_du_post(rr["uri"]))
        except Exception as e:
            sortie("  ⚠ la réponse n'est pas partie (%s) : le post, lui, est en ligne" % e)
    return url


def _envoyer_youtube(fiche, p, sortie, yt=None, fabrique_media=None):
    from publindie import youtube as Y
    t, short = p["textes"], p["reseau"] == "youtube_short"
    if yt is None:
        yt = Y.service(C.SECRETS)
    kw = {"fabrique_media": fabrique_media} if fabrique_media else {}
    v = Y.envoyer(yt, p["medias"][0]["chemin"], p["corps"], t.get("notifier", True), journal=sortie, **kw)
    url = Y.url(v["id"], short)
    demandee = p["corps"]["status"]["privacyStatus"]
    rendue = (v.get("status") or {}).get("privacyStatus", "?")
    FI.marquer(fiche["projet"], fiche["id"], p["reseau"], url, video_id=v["id"], visibilite=rendue, par="publindie")
    sortie("  ✓ ENVOYÉE : %s (journal écrit) — visibilité rendue par YouTube : %s" % (url, rendue))
    if rendue != demandee:
        sortie("  ⚠ YouTube l'a mise en « %s » au lieu de « %s ». Si c'est le verrou des projets non audités : demander "
               "l'audit (YouTube API Services - Audit and Quota Extension Form), puis changer la visibilité dans "
               "YouTube Studio." % (rendue, demandee))
    if p.get("miniature"):
        try:
            Y.miniature(yt, v["id"], p["miniature"], **kw)
            sortie("  ✓ miniature posée")
        except Exception as e:
            sortie("  ⚠ miniature refusée (%s) : la chaîne doit être vérifiée par téléphone "
                   "(youtube.com/verify) ; la vidéo, elle, est en ligne" % e)
    if t.get("playlist"):
        try:
            Y.ajouter_a_playlist(yt, v["id"], t["playlist"])
            sortie("  ✓ ajoutée à la playlist %s" % t["playlist"])
        except Exception as e:
            sortie("  ⚠ playlist refusée (%s)" % e)
    return url


def poster(projet, ident, reseau=None, pour_de_vrai=False, sortie=print, clients=None):
    """Le point d'entrée. `clients` (tests) : {"bluesky": Client, "youtube": service, "fabrique_media": f}.
    Rend OK, REFUS ou SECRET."""
    clients = clients or {}
    fiche = next((f for f in FI.charger_fiches(projet) if f["id"] == ident), None)
    if fiche is None:
        sortie("✗ fiche inconnue : %s/%s" % (projet, ident))
        return REFUS
    vises = reseaux_vises(fiche, reseau)
    if not vises:
        sortie("✗ la fiche %s/%s n'a rien pour %s (Publindie poste sur : %s)" % (
            projet, ident, reseau or "les réseaux automatiques", ", ".join(AUTOMATIQUES)))
        return REFUS
    fautes_fiche = FI.verifier(fiche)
    plans = [plan(fiche, r) for r in vises]
    sortie("%s — %s/%s" % ("POUR DE VRAI" if pour_de_vrai else "ESSAI (rien ne part ; `--pour-de-vrai` pour poster)",
                           projet, ident))
    code = OK
    for p in plans:
        for l in p["lignes"]:
            sortie(l)
        fautes = fautes_fiche + p["fautes"]
        if reseau is None and any(f.startswith("DÉJÀ PARTI") for f in p["fautes"]):
            sortie("  · déjà parti, sauté")
            continue
        if fautes:
            sortie("  ✗ REFUSÉ :")
            for f in fautes:
                sortie("    - %s" % f)
            code = REFUS
            continue
        if not pour_de_vrai:
            _dire_secrets(p["reseau"], projet, sortie)
            sortie("  ✓ prêt (essai)")
            continue
        try:
            if p["reseau"] == "bluesky":
                _envoyer_bluesky(fiche, p, sortie, clients.get("bluesky"))
            else:
                _envoyer_youtube(fiche, p, sortie, clients.get("youtube"), clients.get("fabrique_media"))
        except Exception as e:
            from publindie import bluesky as B
            from publindie import youtube as Y
            if isinstance(e, (B.SecretManquant, Y.SecretManquant)):
                sortie("  ✗ SECRET MANQUANT — rien n'est parti.\n" + str(e))
                return SECRET
            sortie("  ✗ ÉCHEC : %s" % e)
            code = REFUS
    return code


def _dire_secrets(reseau, projet, sortie):
    if reseau == "bluesky":
        from publindie import bluesky as B
        try:
            s = B.charger_secret(C.SECRETS, projet)
            sortie("  compte : %s (%s)" % (s["identifiant"], s["_chemin"].replace("\\", "/")))
        except B.SecretManquant as e:
            sortie("  ⚠ compte non branché : %s" % str(e).split("\n")[0])
            sortie("    (`--pour-de-vrai` s'arrêtera là et dira quoi faire)")
    else:
        from publindie import youtube as Y
        client, jeton = Y.etat_secrets(C.SECRETS)
        sortie("  OAuth : client_secret.json %s, jeton %s (%s)" % (
            "présent" if client else "ABSENT", "présent" if jeton else "absent (consentement au premier lancement)",
            os.path.join(C.SECRETS, "youtube").replace("\\", "/")))
