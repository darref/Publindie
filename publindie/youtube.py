# -*- coding: utf-8 -*-
"""YOUTUBE — Publindie y envoie lui-même vidéos et Shorts (Jordan, 21 octobre 2026 : « Les deux »).

YouTube Data API v3, vérifié le 21 octobre 2026 sur developers.google.com (page `videos.insert` mise à jour le
15 octobre 2026, historique des révisions, `thumbnails.set`) :
- `videos.insert`, ENVOI REPRENABLE (morceaux de 8 Mio, reprise sur les erreurs 5xx) ; portée OAuth `youtube.upload` ;
- ⚠ LE QUOTA A CHANGÉ : depuis juin 2026 `videos.insert` a son PROPRE seau, « Video Uploads » : 100 envois par jour, 1
  unité chacun (l'ancien coût d'environ 1 600 unités sur 10 000, devenu ~100 en décembre 2025, est périmé).
  `thumbnails.set` coûte ~50 unités et `playlistItems.insert` 50, sur les 10 000 unités du seau commun ;
- ⚠ LE VERROU « PRIVÉ » DES PROJETS NON AUDITÉS : la règle du 28 juillet 2020 (« toute vidéo envoyée par un projet non
  vérifié créé après le 28 juillet 2020 est restreinte au mode privé ») figure toujours dans l'historique, mais la
  référence de `videos.insert` dit AUJOURD'HUI : « Videos uploaded from unverified API projects are not restricted to
  private viewing mode. » Les guides de tiers disent encore l'inverse. Publindie ne suppose ni l'un ni l'autre : il
  COMPARE la visibilité que YouTube rend à celle demandée, le DIT, et l'écrit au journal ;
- un SHORT : 3 minutes au plus, carré ou vertical ; le #Shorts n'est plus exigé (support.google.com/youtube/answer/
  15424877). YouTube le classe tout seul ;
- une miniature personnalisée (`thumbnails.set`, JPEG/PNG) n'est permise qu'à une chaîne VÉRIFIÉE par
  téléphone : un refus est dit, il ne défait pas l'envoi.

OAuth « application de bureau » : `<SECRETS>/youtube/client_secret.json` (téléchargé par Jordan depuis Google Cloud),
`<SECRETS>/youtube/jeton.json` (écrit après le consentement de Jordan, dans SON navigateur, puis rafraîchi seul).
⚠ Tant que l'écran de consentement est en mode « Testing », Google fait expirer le jeton de rafraîchissement en 7 JOURS
(developers.google.com/identity/protocols/oauth2) : passer l'appli « In production » (elle reste « non vérifiée » : un
avertissement à cliquer, une seule fois).
"""
import json
import os
import random
import time

PORTEES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]          # youtube : ajouter à une playlist
MORCEAU = 8 * 1024 * 1024
CATEGORIE_JEUX = "20"                                           # « Gaming »
COUT = {"videos.insert": "1 envoi sur 100 par jour (seau « Video Uploads »)", "thumbnails.set": "~50 unités",
        "playlistItems.insert": "50 unités"}

AIDE_SECRET = """YouTube n'est pas branché. À faire UNE FOIS, par Jordan (console.cloud.google.com) :
  1. créer un projet (« Publindie ») ;
  2. APIs & Services → Library → « YouTube Data API v3 » → Enable ;
  3. Google Auth Platform (écran de consentement) : type External, nom « Publindie », son e-mail ; Audience : s'ajouter
     comme utilisateur de test, PUIS « Publish app » (In production) — sinon le jeton expire tous les 7 jours ;
  4. Clients → Create client → type « Desktop app » → télécharger le JSON ;
  5. le déposer, renommé, HORS de tout dépôt :
       %s
  6. lancer `python -m publindie connecter youtube` : le navigateur s'ouvre, choisir la chaîne SpannerGames,
     accepter (l'appli « non vérifiée » : Advanced → Go to Publindie). Le jeton s'écrit à côté ; on ne le refait plus.
  7. (facultatif) demander l'audit (« YouTube API Services - Audit and Quota Extension Form ») si un jour les vidéos
     ressortent privées ou si 100 envois par jour ne suffisent plus."""


class SecretManquant(Exception):
    pass


def chemins_secrets(dossier_secrets):
    d = os.path.join(dossier_secrets, "youtube")
    return os.path.join(d, "client_secret.json"), os.path.join(d, "jeton.json")


def etat_secrets(dossier_secrets):
    """(client_secret présent, jeton présent) — sans rien ouvrir ni contacter."""
    c, j = chemins_secrets(dossier_secrets)
    return os.path.isfile(c), os.path.isfile(j)


def service(dossier_secrets, consentir=True):
    """Le service YouTube authentifié. Le premier lancement ouvre le navigateur (`consentir`) : c'est Jordan qui
    consent, jamais Publindie à sa place. Lève SecretManquant si le client_secret.json manque."""
    client, jeton = chemins_secrets(dossier_secrets)
    if not os.path.isfile(client):
        raise SecretManquant(AIDE_SECRET % client.replace("\\", "/"))
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    cred = Credentials.from_authorized_user_file(jeton, PORTEES) if os.path.isfile(jeton) else None
    if cred and cred.expired and cred.refresh_token:
        try:
            cred.refresh(Request())
        except Exception as e:                                   # jeton révoqué ou expiré (mode Testing : 7 jours)
            print("  ⚠ le jeton YouTube ne se rafraîchit plus (%s) : nouveau consentement" % e)
            cred = None
    if not cred or not cred.valid:
        if not consentir:
            raise SecretManquant("YouTube : pas de jeton valide. Lancer `python -m publindie connecter youtube`.")
        from google_auth_oauthlib.flow import InstalledAppFlow
        flux = InstalledAppFlow.from_client_secrets_file(client, PORTEES)
        cred = flux.run_local_server(port=0, open_browser=True,
                                     authorization_prompt_message="Consentement YouTube dans le navigateur : {url}")
    os.makedirs(os.path.dirname(jeton), exist_ok=True)
    with open(jeton + ".tmp", "w", encoding="utf-8") as h:
        h.write(cred.to_json())
    os.replace(jeton + ".tmp", jeton)
    return build("youtube", "v3", credentials=cred, cache_discovery=False)


def corps(t, short=False):
    """Le corps de `videos.insert` depuis les textes d'un réseau de la fiche (`fiches.textes`)."""
    statut = {"privacyStatus": t.get("visibilite", "public"),
              "selfDeclaredMadeForKids": bool(t.get("pour_enfants", False)),
              "containsSyntheticMedia": bool(t.get("contenu_synthetique", False))}
    if t.get("publier_a"):                                        # une sortie programmée : privée jusqu'à l'heure dite
        statut.update(privacyStatus="private", publishAt=t["publier_a"])
    snippet = {"title": t["titre"], "description": t.get("texte", ""), "categoryId": str(t.get("categorie",
                                                                                               CATEGORIE_JEUX)),
               "defaultLanguage": t.get("langue", "en"), "defaultAudioLanguage": t.get("langue", "en")}
    if t.get("tags"):
        snippet["tags"] = list(t["tags"])
    return {"snippet": snippet, "status": statut}


def _media(chemin, type_mime, reprenable=True):
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(chemin, mimetype=type_mime, chunksize=MORCEAU if reprenable else -1, resumable=reprenable)


def envoyer(yt, chemin, corps_video, notifier=True, fabrique_media=_media, journal=print, essais_max=8):
    """`videos.insert` reprenable ; les erreurs 500/502/503/504 se reprennent (attente exponentielle), les autres
    remontent. Rend la ressource vidéo de YouTube (id, status.privacyStatus…)."""
    requete = yt.videos().insert(part="snippet,status", body=corps_video, notifySubscribers=notifier,
                                 media_body=fabrique_media(chemin, "video/*"))
    reponse, essais = None, 0
    while reponse is None:
        try:
            etat, reponse = requete.next_chunk()
            if etat is not None:
                journal("    envoi : %d %%" % int(etat.progress() * 100))
        except Exception as e:
            code = getattr(getattr(e, "resp", None), "status", None)
            if code not in (500, 502, 503, 504) or essais >= essais_max:
                raise
            essais += 1
            attente = random.random() * (2 ** essais)
            journal("    ⚠ YouTube %s, reprise dans %.0f s (%d/%d)" % (code, attente, essais, essais_max))
            time.sleep(attente)
    return reponse


def miniature(yt, video_id, chemin, fabrique_media=_media):
    type_mime = "image/png" if chemin.lower().endswith(".png") else "image/jpeg"
    return yt.thumbnails().set(videoId=video_id, media_body=fabrique_media(chemin, type_mime, False)).execute()


def ajouter_a_playlist(yt, video_id, playlist):
    return yt.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": playlist, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()


def url(video_id, short=False):
    return ("https://www.youtube.com/shorts/%s" if short else "https://youtu.be/%s") % video_id
