# -*- coding: utf-8 -*-
"""BLUESKY — Publindie y poste lui-même (Jordan, 21 octobre 2026 : « Les deux », Bluesky et YouTube).

HTTP pur (urllib), sans SDK : l'AT Protocol est un ensemble d'appels XRPC en JSON. Vérifié le 21 octobre 2026 sur
docs.bsky.app (le tutoriel vidéo, le guide des posts, le guide des facettes) et sur les lexiques de
`bluesky-social/atproto` (`app.bsky.feed.post`, `app.bsky.embed.images`, `app.bsky.embed.video`, `app.bsky.video.*`) :

1. `com.atproto.server.createSession` avec un MOT DE PASSE D'APPLICATION (jamais le mot de passe du compte) ;
2. le texte et ses FACETTES : liens et hashtags, bornés en OCTETS UTF-8 (pas en caractères) ;
3. une image : `com.atproto.repo.uploadBlob` (2 000 000 octets au plus, 4 images, un texte alternatif chacune) ;
   une vidéo : la voie RECOMMANDÉE par la doc — un jeton `getServiceAuth` (audience : le PDS du compte, méthode
   `com.atproto.repo.uploadBlob`, 30 minutes), l'envoi à `video.bsky.app` (`app.bsky.video.uploadVideo`), puis
   `getJobStatus` jusqu'à ce que le traitement rende le blob. (`uploadBlob` direct marche aussi, mais le post paraît
   avant que la vidéo soit traitée : une vidéo manquante pendant quelques secondes.) MP4 seulement, 300 000 000 octets ;
   un quota par JOUR (`getUploadLimits`), et l'adresse e-mail du compte doit être vérifiée ;
   un GIF n'est pas animé comme image : il part en MP4 avec `presentation: "gif"` (ce que fait l'appli Bluesky) ;
4. `com.atproto.repo.createRecord` (`app.bsky.feed.post`) ; une `premiere_reponse` part en réponse au post.

Le secret : `<SECRETS>/bluesky_<Projet>.json`, sinon `<SECRETS>/bluesky.json` :
    {"identifiant": "spannergames.bsky.social", "mot_de_passe_application": "xxxx-xxxx-xxxx-xxxx"}
(`service` et `service_video` facultatifs : https://bsky.social et https://video.bsky.app.)
"""
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

SERVICE = "https://bsky.social"
SERVICE_VIDEO = "https://video.bsky.app"
APPLI = "https://bsky.app"
# Un mot de passe d'application Bluesky : quatre groupes de quatre, séparés par des tirets.
MOT_DE_PASSE_APPLICATION = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$")

AIDE_SECRET = """Le compte Bluesky n'est pas branché. À faire UNE FOIS, par Jordan :
  1. sur bsky.app, connecté au compte qui doit poster : Settings → Privacy and security → App passwords →
     « Add App Password », nommé « Publindie » (sans accès aux messages privés) ; copier le mot de passe affiché
     (xxxx-xxxx-xxxx-xxxx : il ne se réaffiche jamais) ;
  2. vérifier l'adresse e-mail du compte (Settings → Account) : sans elle, Bluesky refuse les vidéos ;
  3. écrire ce fichier (HORS de tout dépôt) :
       %s
     {"identifiant": "<le pseudo, ex. spannergames.bsky.social>", "mot_de_passe_application": "xxxx-xxxx-xxxx-xxxx"}
  Un compte par projet : bluesky_<Projet>.json dans le même dossier ; sinon bluesky.json sert à tous."""


class ErreurBluesky(Exception):
    def __init__(self, statut, erreur, message, corps=None):
        Exception.__init__(self, "Bluesky %s %s : %s" % (statut, erreur, message))
        self.statut, self.erreur, self.message, self.corps = statut, erreur, message, corps or {}


class SecretManquant(Exception):
    pass


# ---------------------------------------------------------------- le secret

def chemin_secret(dossier_secrets, projet):
    propre = os.path.join(dossier_secrets, "bluesky_%s.json" % projet)
    return propre if os.path.isfile(propre) else os.path.join(dossier_secrets, "bluesky.json")


def charger_secret(dossier_secrets, projet):
    """Le compte d'un projet. Lève SecretManquant (avec le mode d'emploi) si rien n'est déposé ou si ce n'est pas un
    mot de passe d'APPLICATION."""
    p = chemin_secret(dossier_secrets, projet)
    if not os.path.isfile(p):
        raise SecretManquant(AIDE_SECRET % p.replace("\\", "/"))
    with open(p, encoding="utf-8") as h:
        s = json.load(h)
    if not s.get("identifiant") or not s.get("mot_de_passe_application"):
        raise SecretManquant("%s : il faut « identifiant » et « mot_de_passe_application »" % p)
    if not MOT_DE_PASSE_APPLICATION.match(s["mot_de_passe_application"]):
        raise SecretManquant("%s : ce n'est pas un MOT DE PASSE D'APPLICATION (xxxx-xxxx-xxxx-xxxx). Le mot de passe du "
                             "compte ne se dépose jamais ici : Settings → Privacy and security → App passwords." % p)
    s.setdefault("service", SERVICE)
    s.setdefault("service_video", SERVICE_VIDEO)
    s["_chemin"] = p
    return s


# ---------------------------------------------------------------- le texte et ses facettes

_LIEN = re.compile(r"https?://[^\s<>\"']+")
_HASHTAG = re.compile(r"(?:^|(?<=\s))[#＃]([^\s#＃]+)")
_PONCTUATION_FINALE = ".,;:!?)]}'\"…»"


def _octets(texte, i):
    return len(texte[:i].encode("utf-8"))


def facettes(texte):
    """Les liens et les hashtags d'un texte, en FACETTES : bornes en octets UTF-8, fin exclue (docs.bsky.app,
    « Rich text facets »). Un hashtag : sans le #, pas que des chiffres, 64 caractères au plus ; la ponctuation qui le
    suit n'en fait pas partie (même règle que l'appli)."""
    sortie = []
    for m in _LIEN.finditer(texte):
        url = m.group(0).rstrip(_PONCTUATION_FINALE)
        if url.count("(") < url.count(")") and url.endswith(")"):
            url = url[:-1]
        debut = m.start()
        sortie.append({"index": {"byteStart": _octets(texte, debut), "byteEnd": _octets(texte, debut + len(url))},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]})
    for m in _HASHTAG.finditer(texte):
        tag = m.group(1).rstrip(_PONCTUATION_FINALE)
        if not tag or tag.isdigit() or len(tag) > 64:
            continue
        debut = m.start()                       # le #
        if any(f["index"]["byteStart"] <= _octets(texte, debut) < f["index"]["byteEnd"] for f in sortie):
            continue                            # un # dans un lien (une ancre) n'est pas un hashtag
        sortie.append({"index": {"byteStart": _octets(texte, debut), "byteEnd": _octets(texte, debut + 1 + len(tag))},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag}]})
    return sorted(sortie, key=lambda f: f["index"]["byteStart"])


# ---------------------------------------------------------------- le client

class Client:
    """Une session Bluesky. `attente` : secondes entre deux questions au service vidéo (0 dans les tests)."""

    def __init__(self, secret, attente=2.0, delai_video=900):
        self.secret = secret
        self.service = secret["service"].rstrip("/")
        self.service_video = secret["service_video"].rstrip("/")
        self.attente, self.delai_video = attente, delai_video
        self.session = None
        self.pds = self.service

    # -- le transport
    def _appel(self, base, nsid, params=None, corps=None, jeton=None, type_corps="application/json", delai=120):
        url = "%s/xrpc/%s" % (base, nsid)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        donnees = None
        if corps is not None:
            donnees = json.dumps(corps).encode("utf-8") if type_corps == "application/json" else corps
        req = urllib.request.Request(url, data=donnees, method="POST" if corps is not None else "GET")
        if donnees is not None:
            req.add_header("Content-Type", type_corps)
            req.add_header("Content-Length", str(len(donnees)))
        if jeton:
            req.add_header("Authorization", "Bearer " + jeton)
        try:
            with urllib.request.urlopen(req, timeout=delai) as r:
                brut = r.read()
        except urllib.error.HTTPError as e:
            brut = e.read()
            try:
                j = json.loads(brut.decode("utf-8") or "{}")
            except ValueError:
                j = {}
            raise ErreurBluesky(e.code, j.get("error", ""), j.get("message", brut[:200]), j)
        return json.loads(brut.decode("utf-8") or "{}")

    def _jeton(self):
        return self.session["accessJwt"]

    # -- la session
    def ouvrir(self):
        self.session = self._appel(self.service, "com.atproto.server.createSession",
                                   corps={"identifier": self.secret["identifiant"],
                                          "password": self.secret["mot_de_passe_application"]})
        for s in (self.session.get("didDoc") or {}).get("service", []):
            if s.get("id", "").endswith("#atproto_pds") and s.get("serviceEndpoint"):
                self.pds = s["serviceEndpoint"].rstrip("/")
        return self.session

    # -- les médias
    def envoyer_image(self, chemin, type_mime):
        with open(chemin, "rb") as h:
            donnees = h.read()
        return self._appel(self.pds, "com.atproto.repo.uploadBlob", corps=donnees, jeton=self._jeton(),
                           type_corps=type_mime)["blob"]

    def _jeton_service(self, audience, methode, secondes=1800):
        return self._appel(self.pds, "com.atproto.server.getServiceAuth", jeton=self._jeton(),
                           params={"aud": audience, "lxm": methode, "exp": int(time.time()) + secondes})["token"]

    def limites_video(self):
        jeton = self._jeton_service("did:web:" + urllib.parse.urlparse(self.service_video).netloc,
                                    "app.bsky.video.getUploadLimits", 60)
        return self._appel(self.service_video, "app.bsky.video.getUploadLimits", jeton=jeton)

    def envoyer_video(self, chemin, journal=print):
        """La voie recommandée : video.bsky.app traite la vidéo et la range sur le PDS ; on attend le blob."""
        limites = self.limites_video()
        if not limites.get("canUpload", False):
            raise ErreurBluesky(0, "LimiteVideo", limites.get("message") or limites.get("error") or
                                "Bluesky refuse une vidéo de plus aujourd'hui (ou l'e-mail du compte n'est pas vérifié)")
        jeton = self._jeton_service("did:web:" + urllib.parse.urlparse(self.pds).netloc, "com.atproto.repo.uploadBlob")
        with open(chemin, "rb") as h:
            donnees = h.read()
        try:
            r = self._appel(self.service_video, "app.bsky.video.uploadVideo", corps=donnees, jeton=jeton,
                            params={"did": self.session["did"], "name": os.path.basename(chemin)},
                            type_corps="video/mp4", delai=1800)
        except ErreurBluesky as e:            # « already_exists » : le service rend le blob déjà traité
            if e.corps.get("jobId") or e.corps.get("blob"):
                r = e.corps
            else:
                raise
        statut = r.get("jobStatus", r)
        blob, fin = statut.get("blob"), time.time() + self.delai_video
        while not blob:
            if statut.get("state") == "JOB_STATE_FAILED":
                raise ErreurBluesky(0, statut.get("failureCode", "JOB_STATE_FAILED"),
                                    statut.get("error") or statut.get("message") or "traitement refusé")
            if time.time() > fin:
                raise ErreurBluesky(0, "Delai", "la vidéo n'est pas traitée après %d s" % self.delai_video)
            time.sleep(self.attente)
            try:
                statut = self._appel(self.service_video, "app.bsky.video.getJobStatus",
                                     params={"jobId": statut["jobId"]})["jobStatus"]
            except ErreurBluesky as e:
                if (e.corps.get("jobStatus") or {}).get("blob"):
                    statut = e.corps["jobStatus"]
                else:
                    raise
            journal("    vidéo : %s %s" % (statut.get("state", "?"), statut.get("progress", "")))
            blob = statut.get("blob")
        return blob

    # -- le post
    def poster(self, texte, embed=None, langs=("en",), reponse_a=None):
        record = {"$type": "app.bsky.feed.post", "text": texte, "langs": list(langs),
                  "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")}
        f = facettes(texte)
        if f:
            record["facets"] = f
        if embed:
            record["embed"] = embed
        if reponse_a:
            record["reply"] = {"root": reponse_a, "parent": reponse_a}
        return self._appel(self.pds, "com.atproto.repo.createRecord", jeton=self._jeton(),
                           corps={"repo": self.session["did"], "collection": "app.bsky.feed.post", "record": record})

    def url_du_post(self, uri):
        """at://did/app.bsky.feed.post/<rkey> → https://bsky.app/profile/<pseudo>/post/<rkey>."""
        rkey = uri.rsplit("/", 1)[-1]
        return "%s/profile/%s/post/%s" % (APPLI, self.session.get("handle") or self.session["did"], rkey)
