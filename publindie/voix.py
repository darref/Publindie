# -*- coding: utf-8 -*-
"""LA VOIX DE SYNTHÈSE — un texte anglais devient une piste de narration et ses sous-titres.

    .venv/Scripts/python -m publindie.voix TEXTE.txt SORTIE.wav [--voix am_michael] [--vitesse 1.0]

Écrit SORTIE.wav (24 kHz) et SORTIE.srt : une phrase par sous-titre, aux temps RÉELS de la voix —
mesurés sur l'audio produit, pas estimés au nombre de mots.

⚠ LE MOTEUR EST KOKORO-82M (licence Apache 2.0, poids et code) : local, gratuit, utilisable dans une
vidéo monétisée. Il tourne sur la RTX 2060. Le premier lancement télécharge le modèle (~330 Mo).
⚠ ON LE DIT DANS LA DESCRIPTION : « Narration: synthetic voice. » La règle de YouTube n'impose la
mention que pour un contenu RÉALISTE qui tromperait (une vraie personne, un vrai événement) ; une voix
de narration n'en est pas — mais un public de développeurs le reconnaît à l'oreille, et le dire avant
qu'il le demande coûte une ligne. ⚠ Pas de voix d'une personne réelle, jamais.
⚠ LE TEXTE EST EN ANGLAIS : les chaînes du studio parlent anglais (le public est mondial, les produits
aussi). Le français de Jordan est la matière, pas la sortie.
"""
import argparse
import os
import re

import numpy as np
import soundfile as sf

# ⚠ LE LEXIQUE DES NOMS PROPRES : la voix les lit comme des mots anglais. Mesuré en faisant retranscrire
# la voix par Whisper : « Godot » sortait « God-ot », « MarchingBlocks » sortait « Marching block ».
# On réécrit ce que la voix LIT (notation Kokoro `[mot](/API/)`) ; les sous-titres gardent le texte.
LEXIQUE = {
    "MarchingBlocks": "Marching Blocks",
    "SpannerGames": "Spanner Games",
    "SoluTiles": "[SoluTiles](/sˈoʊljuːtaɪlz/)",
    "Godot": "[Godot](/ɡˈoʊdoʊ/)",
}
TAUX = 24000
PAUSE = 0.35  # silence entre deux phrases, en secondes


def phrases(texte):
    texte = re.sub(r"\s+", " ", texte).strip()
    return [p for p in re.split(r"(?<=[.!?])\s+", texte) if p]


def a_lire(phrase):
    for nom, dit in LEXIQUE.items():
        phrase = re.sub(r"\b" + re.escape(nom) + r"\b", dit, phrase)
    return phrase


def horodatage(t):
    ms = round(t * 1000)
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("texte"); p.add_argument("sortie")
    p.add_argument("--voix", default="am_michael")
    p.add_argument("--vitesse", type=float, default=1.0)
    a = p.parse_args()
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code="a" if a.voix[0] == "a" else "b")
    morceaux, sous_titres, t = [], [], 0.0
    silence = np.zeros(int(PAUSE * TAUX), dtype=np.float32)
    for i, ph in enumerate(phrases(open(a.texte, encoding="utf-8").read()), 1):
        audio = np.concatenate([np.asarray(r.audio, dtype=np.float32)
                                for r in pipeline(a_lire(ph), voice=a.voix, speed=a.vitesse)])
        debut, t = t, t + len(audio) / TAUX
        sous_titres.append("%d\n%s --> %s\n%s\n" % (i, horodatage(debut), horodatage(t), ph))
        morceaux += [audio, silence]
        t += PAUSE
    sf.write(a.sortie, np.concatenate(morceaux), TAUX)
    srt = os.path.splitext(a.sortie)[0] + ".srt"
    with open(srt, "w", encoding="utf-8") as f:
        f.write("\n".join(sous_titres))
    print("voix : %s (%.1f s), sous-titres : %s" % (a.sortie, t, srt))


if __name__ == "__main__":
    main()
