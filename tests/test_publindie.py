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
