# -*- coding: utf-8 -*-
"""LES TESTS DE PUBLINDIE — sur un studio JETABLE (un dossier temporaire), jamais sur celui de SpannerGames.

    python -m unittest discover -s tests -v

Les attendus sont écrits à la main ici (les limites, les comptes, les chemins), pas recalculés par le code éprouvé.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))


def _studio():
    d = tempfile.mkdtemp(prefix="publindie_")
    os.makedirs(os.path.join(d, "PROJETS", "Jeu", "04_exports", "gif"))
    os.makedirs(os.path.join(d, "PROJETS", "Jeu", "07_publication", "fiches"))
    with open(os.path.join(d, "publindie.json"), "w", encoding="utf-8") as f:
        json.dump({"projets": {"Jeu": d}}, f)
    with open(os.path.join(d, "PROJETS", "Jeu", "04_exports", "gif", "tour.gif"), "wb") as f:
        f.write(b"GIF89a" + b"\0" * 2048)                 # 2 Ko : un « GIF » que ffprobe ne lit pas, le poids seul compte
    with open(os.path.join(d, "PROJETS", "Jeu", "04_exports", "orphelin.mp4"), "wb") as f:
        f.write(b"\0" * 10)
    return d


def _recharger(studio):
    os.environ["PUBLINDIE_STUDIO"] = studio
    from publindie import chemins, fiches, rangement
    importlib.reload(chemins)
    importlib.reload(fiches)
    importlib.reload(rangement)
    return chemins, fiches, rangement


class Reseaux(unittest.TestCase):
    def test_x_compte_un_lien_pour_23(self):
        from publindie import reseaux as R
        texte = "a" * 250 + " https://exemple.org/" + "b" * 200
        self.assertEqual(R.longueur(texte, "x"), 250 + 1 + 23)
        self.assertEqual(R.longueur(texte, "bluesky"), len(texte))

    def test_le_lien_sur_x_va_en_reponse(self):
        from publindie import reseaux as R
        self.assertTrue(any("PREMIÈRE RÉPONSE" in f for f in R.verifier_texte("x", "voici https://a.b")))
        self.assertEqual(R.verifier_texte("x", "sans lien"), [])

    def test_longueurs(self):
        from publindie import reseaux as R
        self.assertEqual(R.verifier_texte("bluesky", "x" * 300), [])
        self.assertEqual(len(R.verifier_texte("bluesky", "x" * 301)), 1)
        self.assertEqual(len(R.verifier_texte("youtube", "texte", "t" * 101)), 1)
        self.assertEqual(len(R.verifier_texte("youtube", "texte")), 1)          # un titre manque
        self.assertEqual(len(R.verifier_texte("instagram", " ".join("#h%d" % i for i in range(31)))), 1)

    def test_medias(self):
        from publindie import reseaux as R
        self.assertEqual(R.verifier_media("x", "gif", mo=14.9), [])
        self.assertEqual(len(R.verifier_media("x", "gif", mo=15.1)), 1)
        self.assertEqual(len(R.verifier_media("tiktok", "short", secondes=30, largeur=1920, hauteur=1080)), 1)
        self.assertEqual(R.verifier_media("tiktok", "short", secondes=30, largeur=1080, hauteur=1920), [])
        self.assertEqual(len(R.verifier_media("youtube", "gif")), 1)             # YouTube ne prend pas de GIF


class Fiches(unittest.TestCase):
    def setUp(self):
        self.studio = _studio()
        self.C, self.FI, self.RG = _recharger(self.studio)
        fiche = {"id": "tour", "projet": "Jeu", "lien": "https://demo.example", "medias": {"gif_x": "04_exports/gif/tour.gif"},
                 "reseaux": {"x": {"media": "gif_x", "texte": "Un tour.", "premiere_reponse": "Demo: {lien}",
                                   "prevu": "2026-10-21"},
                             "mastodon": {"media": "gif_x", "texte": "Un tour.", "alt": "une île"}}}
        with open(os.path.join(self.studio, "PROJETS", "Jeu", "07_publication", "fiches", "tour.json"), "w",
                  encoding="utf-8") as f:
            json.dump(fiche, f)

    def test_une_bonne_fiche_passe(self):
        self.assertEqual(self.FI.verifier(self.FI.charger_fiches("Jeu")[0]), [])

    def test_un_media_absent_et_un_texte_trop_long_sont_dits(self):
        f = self.FI.charger_fiches("Jeu")[0]
        f["medias"]["gif_x"] = "04_exports/gif/absent.gif"
        f["reseaux"]["mastodon"]["texte"] = "m" * 501
        fautes = self.FI.verifier(f)
        self.assertTrue(any("absent" in x for x in fautes))
        self.assertTrue(any("501" in x for x in fautes))

    def test_le_lien_est_remplace(self):
        f = self.FI.charger_fiches("Jeu")[0]
        self.assertEqual(self.FI.textes(f, "x")["premiere_reponse"], "Demo: https://demo.example")

    def test_marquer_et_preparer(self):
        self.FI.marquer("Jeu", "tour", "x", "https://x.com/1", "2026-10-21")
        j = self.FI.charger_journal("Jeu")
        self.assertEqual(j["tour"]["x"], {"date": "2026-10-21", "url": "https://x.com/1"})
        chemin, fautes = self.FI.preparer(self.FI.charger_fiches("Jeu")[0])
        with open(chemin, encoding="utf-8") as h:
            texte = h.read()
        self.assertIn("## X — ✓ posté le 2026-10-21", texte)
        self.assertIn("## Mastodon — à poster", texte)
        self.assertEqual(fautes, [])
        with self.assertRaises(KeyError):
            self.FI.marquer("Jeu", "inconnue", "x")
        with self.assertRaises(KeyError):
            self.FI.marquer("Jeu", "tour", "myspace")

    def test_calendrier(self):
        import datetime
        cal = self.FI.calendrier(["Jeu"], datetime.date(2026, 10, 20), 3)
        self.assertEqual(list(cal), [datetime.date(2026, 10, 21)])
        self.assertEqual(cal[datetime.date(2026, 10, 21)], [("Jeu", "tour", "x", False)])

    def test_rangement(self):
        r = self.RG.rapport("Jeu")
        self.assertEqual(r["orphelins"], ["04_exports/orphelin.mp4"])         # le GIF est cité par la fiche
        self.assertIn("04_exports", r["dossiers"])
        crees = self.RG.init("Jeu")
        self.assertIn("02_rushes", crees)
        self.assertNotIn("04_exports", crees)                                  # rien n'est écrasé


if __name__ == "__main__":
    unittest.main()


def _ffmpeg_present():
    import shutil
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class Destinations(unittest.TestCase):
    def test_itch_refuse_plus_de_3_mo(self):
        from publindie import destinations as D
        self.assertEqual(D.verifier_piece("itch", "capture", "image", 1920, 1080, 2.9), [])
        self.assertEqual(len(D.verifier_piece("itch", "capture", "gif", 960, 540, 3.2)), 1)

    def test_steam_tailles(self):
        from publindie import destinations as D
        self.assertEqual(D.verifier_piece("steam", "capsule_entete", "image", 920, 430), [])
        self.assertEqual(len(D.verifier_piece("steam", "capsule_entete", "image", 921, 430)), 1)
        self.assertEqual(len(D.verifier_piece("steam", "capture", "image", 1600, 900)), 1)   # trop petite
        self.assertEqual(len(D.verifier_piece("steam", "capture", "gif", 1920, 1080)), 1)    # pas de GIF
        self.assertEqual(len(D.verifier_piece("steam", "capture", "image", 1920, 1200)), 1)  # pas en 16:9

    def test_nombres(self):
        from publindie import destinations as D
        self.assertEqual(len(D.verifier_nombres("steam", {"capture": 4, "capsule_entete": 1, "capsule_petite": 1,
                                                          "capsule_principale": 1, "capsule_verticale": 1,
                                                          "bibliotheque": 1})), 1)
        self.assertEqual(len(D.verifier_nombres("itch", {"couverture": 2, "capture": 3})), 1)


@unittest.skipUnless(_ffmpeg_present(), "ffmpeg absent")
class Vitrine(unittest.TestCase):
    def setUp(self):
        import subprocess
        self.studio = _studio()
        _recharger(self.studio)
        from publindie import vitrine
        importlib.reload(vitrine)
        self.V = vitrine
        p = os.path.join(self.studio, "PROJETS", "Jeu")
        # 6 s de mire animée, 1920 × 1080, un peu bruitée (assez pour qu'un GIF de 960 px dépasse 3 Mo et soit réduit)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=1920x1080:rate=30:duration=6,noise=alls=14:allf=t",
                        "-pix_fmt", "yuv420p", os.path.join(p, "04_exports", "mire.mp4")], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=1920x1080:rate=30:duration=4", "-pix_fmt", "yuv420p",
                        os.path.join(p, "04_exports", "propre.mp4")], check=True)
        from PIL import Image
        Image.new("RGB", (2560, 1440), (40, 120, 200)).save(os.path.join(p, "04_exports", "grande.png"))
        os.makedirs(os.path.join(p, "06_boutique", "itch"))
        os.makedirs(os.path.join(p, "06_boutique", "site"))
        self.p = p

    def _liste(self, dest, pieces):
        with open(os.path.join(self.p, "06_boutique", dest, "vitrine.json"), "w", encoding="utf-8") as f:
            json.dump({"pieces": pieces}, f)

    def test_itch_un_lot_complet(self):
        self._liste("itch", [
            {"role": "couverture", "nom": "cover", "source": "04_exports/propre.mp4", "sorte": "gif", "debut": 0,
             "duree": 6, "largeur": 630, "hauteur": 500, "fps": 15},
            {"role": "capture", "nom": "01", "source": "04_exports/grande.png", "largeur": 1920},
            {"role": "capture", "nom": "02", "source": "04_exports/mire.mp4", "temps": 2, "recadrage": [0, 0, 960, 540]},
            {"role": "capture", "nom": "03", "source": "04_exports/propre.mp4", "sorte": "gif", "duree": 4,
             "largeur": 960, "fps": 15},
        ])
        rapport, fautes = self.V.fabriquer("Jeu", "itch")
        self.assertEqual(fautes, [], rapport)
        par_nom = {l["nom"]: l for l in rapport}
        self.assertEqual((par_nom["cover"]["fichiers"][0]["largeur"], par_nom["cover"]["fichiers"][0]["hauteur"]),
                         (630, 500))
        self.assertEqual(par_nom["01"]["fichiers"][0]["largeur"], 1920)
        self.assertEqual(par_nom["02"]["fichiers"][0]["largeur"], 960)                 # recadré, pas agrandi
        for l in rapport:
            for f in l["fichiers"]:
                self.assertLessEqual(f["mo"], 3.0)
        self.assertTrue(os.path.exists(os.path.join(self.p, "06_boutique", "itch", "lot", "planche.png")))

    def test_une_piece_manquante_et_trop_peu_de_captures(self):
        self._liste("itch", [{"role": "capture", "nom": "x", "source": "04_exports/absent.png"}])
        rapport, fautes = self.V.fabriquer("Jeu", "itch")
        self.assertTrue(any("source absente" in f for f in fautes))
        self.assertTrue(any("au moins 3" in f for f in fautes))
        self.assertTrue(any("couverture" in f for f in fautes))

    def test_site_boucle_et_webp(self):
        self._liste("site", [
            {"role": "boucle", "nom": "tour", "source": "04_exports/propre.mp4", "duree": 3, "largeur": 1280},
            {"role": "image", "nom": "ile", "source": "04_exports/grande.png"},
        ])
        rapport, fautes = self.V.fabriquer("Jeu", "site")
        self.assertEqual(fautes, [], rapport)
        par_nom = {l["nom"]: l for l in rapport}
        exts = sorted(f["fichier"].rsplit(".", 1)[1] for f in par_nom["tour"]["fichiers"])
        self.assertEqual(exts, ["mp4", "webm"])
        self.assertTrue(os.path.exists(os.path.join(self.p, "06_boutique", "site", "lot", "tour.webp")))  # l'attente
        self.assertEqual(sorted(f["largeur"] for f in par_nom["ile"]["fichiers"]), [960, 1920, 2560])


class Capturer(unittest.TestCase):
    def test_recette_et_commande(self):
        studio = _studio()
        _recharger(studio)
        from publindie import capturer as K
        importlib.reload(K)
        r = os.path.join(studio, "r.json")
        with open(r, "w", encoding="utf-8") as f:
            json.dump({"projet": "Jeu", "scene": "res://a.tscn", "taille": [1280, 720], "plans": [
                {"nom": "a", "oeil": [0, 1, 2], "cible": [0, 0, 0]},
                {"nom": "b", "oeil": [0, 1, 2], "cible": [0, 0, 0], "film": {"secondes": 2}}]}, f)
        rec = K.charger(r)
        cmd = K.commande(rec, "/sortie", "/r.json", "b")
        self.assertIn("--fixed-fps", cmd)                       # un film : pas de temps fixe
        self.assertIn("1280x720", cmd)
        self.assertEqual(cmd[-1], "--seulement=b")
        with open(r, "w", encoding="utf-8") as f:
            json.dump({"projet": "Jeu", "scene": "s", "plans": [{"nom": "a", "oeil": [0, 1], "cible": [0, 0, 0]}]}, f)
        with self.assertRaises(SystemExit):
            K.charger(r)


@unittest.skipUnless(_ffmpeg_present(), "ffmpeg absent")
class VitrineRefus(Vitrine):
    """Ce qui ne tient pas est DIT, jamais livré en silence."""
    def test_itch_un_lot_complet(self):
        pass

    def test_site_boucle_et_webp(self):
        pass

    def test_une_piece_manquante_et_trop_peu_de_captures(self):
        pass

    def test_un_gif_trop_lourd_cede_et_le_dit(self):
        from publindie import destinations as D
        self._liste("itch", [{"role": "capture", "nom": "g", "source": "04_exports/propre.mp4", "sorte": "gif",
                              "duree": 4, "largeur": 960, "fps": 15}])
        ancien = D.DESTINATIONS["itch"]["pieces"]["capture"]["mo"]
        D.DESTINATIONS["itch"]["pieces"]["capture"]["mo"] = 0.8
        try:
            rapport, fautes = self.V.fabriquer("Jeu", "itch")
        finally:
            D.DESTINATIONS["itch"]["pieces"]["capture"]["mo"] = ancien
        self.assertTrue(any("GIF cédé" in n for n in rapport[0]["notes"]), rapport[0])
        f = rapport[0]["fichiers"][0]
        self.assertTrue(f["mo"] <= 0.8 or any("dépasse" in n for n in rapport[0]["notes"]), rapport[0])

    def test_une_boucle_trop_lourde_est_refusee(self):
        from publindie import destinations as D
        self._liste("site", [{"role": "boucle", "nom": "lourde", "source": "04_exports/mire.mp4", "duree": 4}])
        ancien = D.DESTINATIONS["site"]["pieces"]["boucle"]["mo"]
        D.DESTINATIONS["site"]["pieces"]["boucle"]["mo"] = 0.004         # 4 ko : impossible, même plafonnée
        try:
            rapport, fautes = self.V.fabriquer("Jeu", "site")
        finally:
            D.DESTINATIONS["site"]["pieces"]["boucle"]["mo"] = ancien
        self.assertTrue(any("Mo, 0.004 au plus" in f for f in fautes), fautes)
        self.assertTrue(any("plafonnée" in n for n in rapport[0]["notes"]))
