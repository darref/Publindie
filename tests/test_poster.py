# -*- coding: utf-8 -*-
"""LES TESTS DE `poster` — un studio JETABLE, un FAUX serveur Bluesky (http.server sur 127.0.0.1) et un FAUX service
YouTube : aucun appel réseau réel, aucun compte, aucun secret vrai.

Les attendus sont écrits à la main (bornes des facettes comptées à la main, URL, corps envoyés).
"""
import importlib
import io
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))


def _png(chemin, w=4, h=2):
    """Un vrai PNG minuscule, écrit à la main (Pillow n'est pas exigé pour l'écrire)."""
    brut = b"".join(b"\0" + b"\x80\x40\x20" * w for _ in range(h))
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b""))


# ---------------------------------------------------------------- le faux Bluesky

class FauxBluesky(BaseHTTPRequestHandler):
    appels = []                 # (méthode, nsid, params, en-têtes utiles, corps)
    etats_video = []

    def log_message(self, *a):
        pass

    def _repondre(self, code, obj):
        d = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def _traiter(self, corps):
        u = urlparse(self.path)
        nsid = u.path.rsplit("/", 1)[-1]
        params = {k: v[0] for k, v in parse_qs(u.query).items()}
        FauxBluesky.appels.append((self.command, nsid, params, {"auth": self.headers.get("Authorization"),
                                                               "type": self.headers.get("Content-Type")}, corps))
        base = "http://%s:%d" % self.server.server_address
        if nsid == "com.atproto.server.createSession":
            j = json.loads(corps)
            if j["password"] != "abcd-efgh-ijkl-mnop":
                return self._repondre(401, {"error": "AuthenticationRequired", "message": "Invalid password"})
            return self._repondre(200, {"accessJwt": "JETON", "refreshJwt": "R", "did": "did:plc:studio",
                                        "handle": "studio.test", "emailConfirmed": True,
                                        "didDoc": {"service": [{"id": "#atproto_pds", "type": "AtprotoPersonalDataServer",
                                                                "serviceEndpoint": base}]}})
        if nsid == "com.atproto.server.getServiceAuth":
            return self._repondre(200, {"token": "SERVICE-" + params["lxm"]})
        if nsid == "app.bsky.video.getUploadLimits":
            return self._repondre(200, {"canUpload": True, "remainingDailyVideos": 24})
        if nsid == "app.bsky.video.uploadVideo":
            return self._repondre(200, {"jobStatus": {"jobId": "job1", "did": "did:plc:studio",
                                                      "state": "JOB_STATE_CREATED"}})
        if nsid == "app.bsky.video.getJobStatus":
            etat = FauxBluesky.etats_video.pop(0)
            return self._repondre(200, {"jobStatus": etat})
        if nsid == "com.atproto.repo.uploadBlob":
            return self._repondre(200, {"blob": {"$type": "blob", "ref": {"$link": "bafyimage"},
                                                 "mimeType": self.headers.get("Content-Type"), "size": len(corps)}})
        if nsid == "com.atproto.repo.createRecord":
            n = sum(1 for a in FauxBluesky.appels if a[1] == nsid)
            return self._repondre(200, {"uri": "at://did:plc:studio/app.bsky.feed.post/3post%d" % n, "cid": "cid%d" % n})
        return self._repondre(404, {"error": "MethodNotImplemented", "message": nsid})

    def do_GET(self):
        self._traiter(b"")

    def do_POST(self):
        self._traiter(self.rfile.read(int(self.headers.get("Content-Length", 0))))


# ---------------------------------------------------------------- le faux YouTube

class _Etat:
    def __init__(self, p):
        self.p = p

    def progress(self):
        return self.p


class FauxYouTube:
    def __init__(self, visibilite_rendue="public", miniature_refusee=False):
        self.inserts, self.miniatures, self.playlists = [], [], []
        self.visibilite_rendue, self.miniature_refusee = visibilite_rendue, miniature_refusee

    def videos(self):
        yt = self

        class V:
            def insert(self, part, body, notifySubscribers, media_body):
                yt.inserts.append({"part": part, "body": body, "notifier": notifySubscribers, "media": media_body})
                morceaux = [(_Etat(0.5), None), (None, {"id": "VID123", "status": {
                    "privacyStatus": yt.visibilite_rendue, "uploadStatus": "uploaded"}})]

                class R:
                    def next_chunk(self):
                        return morceaux.pop(0)
                return R()
        return V()

    def thumbnails(self):
        yt = self

        class T:
            def set(self, videoId, media_body):
                class R:
                    def execute(self):
                        if yt.miniature_refusee:
                            raise RuntimeError("403 forbidden")
                        yt.miniatures.append((videoId, media_body))
                        return {}
                return R()
        return T()

    def playlistItems(self):
        yt = self

        class P:
            def insert(self, part, body):
                class R:
                    def execute(self):
                        yt.playlists.append(body)
                        return {}
                return R()
        return P()


def _fabrique(chemin, type_mime, reprenable=True):
    return ("media", chemin, type_mime, reprenable)


# ---------------------------------------------------------------- le studio jetable

def _studio():
    d = tempfile.mkdtemp(prefix="publindie_poster_")
    p = os.path.join(d, "PROJETS", "Jeu")
    os.makedirs(os.path.join(p, "04_exports"))
    os.makedirs(os.path.join(p, "07_publication", "fiches"))
    with open(os.path.join(d, "publindie.json"), "w", encoding="utf-8") as f:
        json.dump({"projets": {"Jeu": d}}, f)
    _png(os.path.join(p, "04_exports", "ile.png"))
    _png(os.path.join(p, "04_exports", "miniature.png"))
    with open(os.path.join(p, "04_exports", "tour.mp4"), "wb") as f:
        f.write(b"\0\0\0\x18ftypmp42" + b"\0" * 4000)        # un « MP4 » : seul le poids compte pour le faux serveur
    with open(os.path.join(p, "04_exports", "short_tour.mp4"), "wb") as f:
        f.write(b"\0" * 3000)
    secrets = os.path.join(d, "secrets_hors_git")
    os.makedirs(os.path.join(secrets, "youtube"))
    return d, p, secrets


def _recharger(studio, secrets):
    os.environ["PUBLINDIE_STUDIO"] = studio
    os.environ["PUBLINDIE_SECRETS"] = secrets
    from publindie import chemins, fiches, poster, bluesky, youtube
    for m in (chemins, fiches, bluesky, youtube, poster):
        importlib.reload(m)
    return fiches, poster, bluesky


TEXTE = "Une île ✨ https://demo.example/x. #gamedev #indiedev"


class Poster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serveur = ThreadingHTTPServer(("127.0.0.1", 0), FauxBluesky)
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.serveur.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()

    def setUp(self):
        FauxBluesky.appels = []
        self.studio, self.p, self.secrets = _studio()
        self.FI, self.P, self.B = _recharger(self.studio, self.secrets)
        self.fiche = {"id": "tour", "projet": "Jeu", "lien": "https://demo.example",
                      "medias": {"image": "04_exports/ile.png", "video": "04_exports/tour.mp4",
                                 "short": "04_exports/short_tour.mp4", "miniature": "04_exports/miniature.png"},
                      "reseaux": {"bluesky": {"media": "image", "texte": TEXTE, "alt": "An island seen from above.",
                                              "premiere_reponse": "Demo: {lien}"},
                                  "youtube": {"media": "video", "titre": "An Island", "texte": "Demo: {lien}",
                                              "tags": ["godot", "level editor"], "miniature": "miniature",
                                              "playlist": "PLjeu"},
                                  "youtube_short": {"media": "short", "titre": "An Island #Shorts", "texte": "Short."}}}
        self._ecrire()

    def _ecrire(self):
        with open(os.path.join(self.p, "07_publication", "fiches", "tour.json"), "w", encoding="utf-8") as f:
            json.dump(self.fiche, f, ensure_ascii=False)

    def _secret_bluesky(self, mdp="abcd-efgh-ijkl-mnop"):
        with open(os.path.join(self.secrets, "bluesky.json"), "w", encoding="utf-8") as f:
            json.dump({"identifiant": "studio.test", "mot_de_passe_application": mdp, "service": self.base,
                       "service_video": self.base}, f)

    def _client(self):
        c = self.B.Client(self.B.charger_secret(self.secrets, "Jeu"), attente=0)
        return c

    def _poster(self, reseau, vrai=True, clients=None):
        lignes = []
        code = self.P.poster("Jeu", "tour", reseau, pour_de_vrai=vrai, sortie=lignes.append, clients=clients)
        return code, "\n".join(lignes)

    # -- les facettes, à la main
    def test_facettes_en_octets(self):
        f = self.B.facettes(TEXTE)
        # « Une île ✨ » : U-n-e-espace (4) + î (2) + l-e-espace (3) + ✨ (3) + espace (1) = 13 octets avant le lien
        self.assertEqual(f[0], {"index": {"byteStart": 13, "byteEnd": 35},
                                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://demo.example/x"}]})
        self.assertEqual([(x["index"]["byteStart"], x["index"]["byteEnd"], x["features"][0]["tag"]) for x in f[1:]],
                         [(37, 45, "gamedev"), (46, 55, "indiedev")])
        self.assertEqual(self.B.facettes("#123 et https://a.b/#ancre"),
                         [{"index": {"byteStart": 8, "byteEnd": 26},
                           "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://a.b/#ancre"}]}])

    def test_graphemes_et_octets(self):
        from publindie import reseaux as R
        famille = "\U0001f468‍❤️‍\U0001f468"               # 1 graphème, 20 octets
        self.assertEqual(R.longueur(famille * 3, "bluesky"), 3)
        self.assertEqual(R.verifier_texte("bluesky", "é" * 300), [])
        self.assertEqual(len(R.verifier_texte("bluesky", "é" * 301)), 1)   # 301 graphèmes
        self.assertTrue(any("octets" in x for x in R.verifier_texte("bluesky", famille * 151)))   # 3 020 octets

    # -- l'essai
    def test_l_essai_n_envoie_rien(self):
        self._secret_bluesky()
        code, sortie = self._poster(None, vrai=False)
        self.assertEqual(code, 0, sortie)
        self.assertEqual(FauxBluesky.appels, [])
        self.assertEqual(self.FI.charger_journal("Jeu"), {})
        self.assertIn("ESSAI", sortie)
        self.assertIn("facette link [13:35] https://demo.example/x", sortie)
        self.assertIn("puis en réponse : Demo: https://demo.example", sortie)
        self.assertIn("titre : An Island", sortie)
        self.assertIn("client_secret.json ABSENT", sortie)

    # -- Bluesky pour de vrai, contre le faux serveur
    def test_bluesky_image(self):
        self._secret_bluesky()
        code, sortie = self._poster("bluesky", clients={"bluesky": self._client()})
        self.assertEqual(code, 0, sortie)
        nsids = [a[1] for a in FauxBluesky.appels]
        self.assertEqual(nsids, ["com.atproto.server.createSession", "com.atproto.repo.uploadBlob",
                                 "com.atproto.repo.createRecord", "com.atproto.repo.createRecord"])
        self.assertEqual(FauxBluesky.appels[1][3], {"auth": "Bearer JETON", "type": "image/png"})
        post = json.loads(FauxBluesky.appels[2][4])["record"]
        self.assertEqual(post["text"], TEXTE)
        self.assertEqual(post["langs"], ["en"])
        self.assertEqual(post["embed"]["images"][0]["alt"], "An island seen from above.")
        self.assertEqual(post["embed"]["images"][0]["aspectRatio"], {"width": 4, "height": 2})
        self.assertEqual(post["facets"][0]["index"], {"byteStart": 13, "byteEnd": 35})
        reponse = json.loads(FauxBluesky.appels[3][4])["record"]
        self.assertEqual(reponse["text"], "Demo: https://demo.example")
        self.assertEqual(reponse["reply"]["parent"], {"uri": "at://did:plc:studio/app.bsky.feed.post/3post1",
                                                      "cid": "cid1"})
        j = self.FI.charger_journal("Jeu")["tour"]["bluesky"]
        self.assertEqual(j["url"], "https://bsky.app/profile/studio.test/post/3post1")
        self.assertEqual(j["par"], "publindie")

    def test_bluesky_video_par_le_service_video(self):
        self._secret_bluesky()
        self.fiche["reseaux"]["bluesky"].update(media="video", alt="A tour.")
        del self.fiche["reseaux"]["bluesky"]["premiere_reponse"]
        self._ecrire()
        FauxBluesky.etats_video = [{"jobId": "job1", "did": "did:plc:studio", "state": "JOB_STATE_ENCODING",
                                    "progress": 40},
                                   {"jobId": "job1", "did": "did:plc:studio", "state": "JOB_STATE_COMPLETED",
                                    "blob": {"$type": "blob", "ref": {"$link": "bafyvideo"}, "mimeType": "video/mp4",
                                             "size": 4012}}]
        code, sortie = self._poster("bluesky", clients={"bluesky": self._client()})
        self.assertEqual(code, 0, sortie)
        nsids = [a[1] for a in FauxBluesky.appels]
        self.assertEqual(nsids, ["com.atproto.server.createSession", "com.atproto.server.getServiceAuth",
                                 "app.bsky.video.getUploadLimits", "com.atproto.server.getServiceAuth",
                                 "app.bsky.video.uploadVideo", "app.bsky.video.getJobStatus",
                                 "app.bsky.video.getJobStatus", "com.atproto.repo.createRecord"])
        auth_envoi = FauxBluesky.appels[3][2]
        self.assertEqual(auth_envoi["lxm"], "com.atproto.repo.uploadBlob")
        self.assertEqual(auth_envoi["aud"], "did:web:127.0.0.1:%d" % self.serveur.server_address[1])
        envoi = FauxBluesky.appels[4]
        self.assertEqual(envoi[2], {"did": "did:plc:studio", "name": "tour.mp4"})
        self.assertEqual(envoi[3], {"auth": "Bearer SERVICE-com.atproto.repo.uploadBlob", "type": "video/mp4"})
        self.assertEqual(len(envoi[4]), 4012)
        embed = json.loads(FauxBluesky.appels[-1][4])["record"]["embed"]
        self.assertEqual(embed["$type"], "app.bsky.embed.video")
        self.assertEqual(embed["video"]["ref"], {"$link": "bafyvideo"})
        self.assertEqual(embed["alt"], "A tour.")

    def test_bluesky_refuse_le_mot_de_passe_du_compte(self):
        self._secret_bluesky("mon-vrai-mot-de-passe")
        code, sortie = self._poster("bluesky")
        self.assertEqual(code, 2, sortie)
        self.assertIn("App passwords", sortie)
        self.assertEqual(FauxBluesky.appels, [])

    def test_secret_bluesky_manquant(self):
        code, sortie = self._poster("bluesky")
        self.assertEqual(code, 2, sortie)
        self.assertIn("bluesky.json", sortie)
        self.assertIn("Settings → Privacy and security → App passwords", sortie)
        self.assertEqual(self.FI.charger_journal("Jeu"), {})

    # -- LES REFUS (les deux mutations gardées par ces tests)
    def test_deja_au_journal_ne_repart_pas(self):
        self._secret_bluesky()
        self.FI.marquer("Jeu", "tour", "bluesky", "https://bsky.app/profile/studio.test/post/ancien", "2026-10-20")
        code, sortie = self._poster("bluesky", clients={"bluesky": self._client()})
        self.assertEqual(code, 1, sortie)
        self.assertIn("DÉJÀ PARTI", sortie)
        self.assertEqual(FauxBluesky.appels, [])
        self.assertEqual(self.FI.charger_journal("Jeu")["tour"]["bluesky"]["date"], "2026-10-20")

    def test_un_texte_trop_long_ne_part_pas(self):
        self._secret_bluesky()
        self.fiche["reseaux"]["bluesky"]["texte"] = "x" * 301
        self._ecrire()
        code, sortie = self._poster("bluesky", clients={"bluesky": self._client()})
        self.assertEqual(code, 1, sortie)
        self.assertIn("301", sortie)
        self.assertEqual(FauxBluesky.appels, [])
        self.assertEqual(self.FI.charger_journal("Jeu"), {})

    def test_une_image_sans_texte_alternatif_ne_part_pas(self):
        self._secret_bluesky()
        del self.fiche["reseaux"]["bluesky"]["alt"]
        self._ecrire()
        code, sortie = self._poster("bluesky", clients={"bluesky": self._client()})
        self.assertEqual(code, 1, sortie)
        self.assertIn("texte alternatif", sortie)
        self.assertEqual(FauxBluesky.appels, [])

    # -- YouTube contre le faux service
    def test_youtube_video_miniature_playlist(self):
        yt = FauxYouTube()
        code, sortie = self._poster("youtube", clients={"youtube": yt, "fabrique_media": _fabrique})
        self.assertEqual(code, 0, sortie)
        envoi = yt.inserts[0]
        self.assertEqual(envoi["part"], "snippet,status")
        self.assertEqual(envoi["body"]["snippet"]["title"], "An Island")
        self.assertEqual(envoi["body"]["snippet"]["description"], "Demo: https://demo.example")
        self.assertEqual(envoi["body"]["snippet"]["tags"], ["godot", "level editor"])
        self.assertEqual(envoi["body"]["snippet"]["categoryId"], "20")
        self.assertEqual(envoi["body"]["status"]["privacyStatus"], "public")
        self.assertEqual(envoi["media"][1].replace("\\", "/").rsplit("/", 2)[1:], ["04_exports", "tour.mp4"])
        self.assertEqual(yt.miniatures[0][0], "VID123")
        self.assertEqual(yt.playlists[0]["snippet"]["playlistId"], "PLjeu")
        j = self.FI.charger_journal("Jeu")["tour"]["youtube"]
        self.assertEqual((j["url"], j["visibilite"]), ("https://youtu.be/VID123", "public"))

    def test_youtube_verrou_prive_dit_et_note(self):
        yt = FauxYouTube(visibilite_rendue="private", miniature_refusee=True)
        code, sortie = self._poster("youtube_short", clients={"youtube": yt, "fabrique_media": _fabrique})
        self.assertEqual(code, 0, sortie)
        self.assertIn("« private » au lieu de « public »", sortie)
        j = self.FI.charger_journal("Jeu")["tour"]["youtube_short"]
        self.assertEqual((j["url"], j["visibilite"]), ("https://www.youtube.com/shorts/VID123", "private"))

    def test_youtube_miniature_refusee_n_annule_pas(self):
        yt = FauxYouTube(miniature_refusee=True)
        code, sortie = self._poster("youtube", clients={"youtube": yt, "fabrique_media": _fabrique})
        self.assertEqual(code, 0, sortie)
        self.assertIn("miniature refusée", sortie)
        self.assertIn("youtube", self.FI.charger_journal("Jeu")["tour"])

    def test_secret_youtube_manquant(self):
        code, sortie = self._poster("youtube")
        self.assertEqual(code, 2, sortie)
        self.assertIn("client_secret.json", sortie)
        self.assertIn("Desktop app", sortie)
        self.assertEqual(self.FI.charger_journal("Jeu"), {})

    def test_youtube_deja_parti_ne_repart_pas(self):
        self.FI.marquer("Jeu", "tour", "youtube", "https://youtu.be/ANCIEN")
        yt = FauxYouTube()
        code, sortie = self._poster("youtube", clients={"youtube": yt, "fabrique_media": _fabrique})
        self.assertEqual(code, 1, sortie)
        self.assertEqual(yt.inserts, [])

    def test_sans_reseau_le_deja_parti_est_saute(self):
        self.FI.marquer("Jeu", "tour", "youtube", "https://youtu.be/ANCIEN")
        code, sortie = self._poster(None, vrai=False)
        self.assertEqual(code, 0, sortie)
        self.assertIn("déjà parti, sauté", sortie)

    def test_la_ligne_de_commande_ne_poste_pas_sans_le_drapeau(self):
        from publindie import __main__ as M
        importlib.reload(M)
        self._secret_bluesky()
        tampon, ancien = io.StringIO(), sys.stdout
        sys.stdout = tampon
        try:
            code = M.main(["poster", "Jeu", "tour", "--reseau", "bluesky"])
            code_les_deux = M.main(["poster", "Jeu", "tour", "--essai", "--pour-de-vrai"])
        finally:
            sys.stdout = ancien
        self.assertEqual(code, 0, tampon.getvalue())
        self.assertEqual(code_les_deux, 1)
        self.assertEqual(FauxBluesky.appels, [])                 # le secret pointe sur le faux serveur : rien reçu
        self.assertIn("ESSAI", tampon.getvalue())


if __name__ == "__main__":
    unittest.main()
