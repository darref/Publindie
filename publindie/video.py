# -*- coding: utf-8 -*-
"""LA BOÎTE À OUTILS VIDÉO — tout le montage est un script, donc refaisable à l'identique.

    python -m publindie.video couper   SOURCE SORTIE --debut 12.5 --duree 8
    python -m publindie.video monter   LISTE.txt SORTIE              # une ligne par plan : fichier [début durée]
    python -m publindie.video musique  VIDEO MUSIQUE SORTIE [--debut-musique 0]
    python -m publindie.video short    SOURCE SORTIE [--centre 0.5]  # 1080 × 1920, recadré
    python -m publindie.video planche  SOURCE SORTIE.png [--pas 5]   # planche de contact, pour CHOISIR
    python -m publindie.video gif      SOURCE SORTIE.gif --debut 3 --duree 8 [--largeur 720 --fps 15]
    python -m publindie.video verifier VIDEO [--short]

⚠ ON MONTE EN COUPES FRANCHES, PAS EN FONDUS. C'est déjà la règle de River Stones (« trois coupes sont
un montage, un travelling est une caméra qui cherche »), et elle vaut pour une boucle de vingt secondes :
un fondu y mange une seconde sur vingt.
⚠ TOUT SORT AU FORMAT YOUTUBE, ET C'EST `verifier` QUI LE DIT, PAS L'ESPOIR : H.264 High en yuv420p,
images progressives, AAC à 48 kHz, `moov` en tête (la lecture démarre avant la fin du téléchargement),
et un son autour de −14 LUFS intégrés — YouTube ramène tout à peu près là : plus fort, il baisse le son
et écrase les pointes ; plus faible, la vidéo paraît molle à côté des autres.
⚠ LE SON PASSE PAR `loudnorm` EN DEUX PASSES : une seule passe mesure en direct et pompe le volume.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from publindie import chemins as C

# ⚠ LA CADENCE SUIT LA SOURCE, ELLE NE S'IMPOSE PAS : les rushes de River Stones sont en 24 images/s,
# et les passer en 30 doublerait une image sur quatre — une saccade régulière, visible sur chaque panoramique.
LUFS = -14.0
CRETE = -1.0
VIDEO_YT = ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
AUDIO_YT = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def ffmpeg(*args):
    cmd = [C.OUTILS["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg a échoué :\n" + r.stderr[-2000:])
    return r


def sonder(chemin):
    r = subprocess.run([C.OUTILS["ffprobe"], "-v", "error", "-print_format", "json",
                        "-show_streams", "-show_format", chemin],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffprobe ne lit pas %s :\n%s" % (chemin, r.stderr))
    return json.loads(r.stdout)


def a_du_son(chemin):
    return any(s["codec_type"] == "audio" for s in sonder(chemin)["streams"])


def mesurer_volume(chemin):
    """Les mesures de loudnorm (première passe) : intégré, crête, plage, seuil."""
    cmd = [C.OUTILS["ffmpeg"], "-hide_banner", "-nostats", "-i", chemin, "-af",
           "loudnorm=I=%s:TP=%s:LRA=11:print_format=json" % (LUFS, CRETE), "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    texte = r.stderr
    return json.loads(texte[texte.rindex("{"):texte.rindex("}") + 1])


def filtre_volume(chemin):
    m = mesurer_volume(chemin)
    return ("loudnorm=I=%s:TP=%s:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
            "measured_thresh=%s:offset=%s:linear=true" % (
                LUFS, CRETE, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"],
                m["target_offset"]))


def cadence(chemin):
    v = next(s for s in sonder(chemin)["streams"] if s["codec_type"] == "video")
    n, d = v["r_frame_rate"].split("/")
    return round(int(n) / int(d), 3)


def plan_normalise(source, sortie, debut=None, duree=None, largeur=1920, hauteur=1080, fps=None):
    """Un plan au format commun (taille, cadence, son stéréo 48 kHz — silence s'il n'en a pas) :
    la concaténation sans réencodage exige des plans IDENTIQUES en tout."""
    entree = []
    if debut is not None:
        entree += ["-ss", str(debut)]
    if duree is not None:
        entree += ["-t", str(duree)]
    # ⚠ `out_range=tv` puis `format=yuv420p` : les rushes MJPEG de Godot sont en plage PLEINE (yuvj420p),
    # et `-pix_fmt yuv420p` seul gardait le drapeau — `verifier` l'a refusé au premier essai.
    image = ("scale=%d:%d:force_original_aspect_ratio=decrease:flags=lanczos:out_range=tv,"
             "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,fps=%s,setsar=1,format=yuv420p" % (largeur, hauteur, largeur, hauteur,
                                                               fps or cadence(source)))
    if a_du_son(source):
        ffmpeg(*entree, "-i", source, "-vf", image, *VIDEO_YT, *AUDIO_YT, sortie)
    else:
        ffmpeg(*entree, "-i", source, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
               "-vf", image, "-shortest", *VIDEO_YT, *AUDIO_YT, sortie)


def couper(a):
    plan_normalise(a.source, a.sortie, a.debut, a.duree)


def monter(a):
    """Une liste de plans → une vidéo, en coupes franches. Les lignes vides et `#` sont ignorées ;
    un chemin relatif se lit depuis le dossier de la liste."""
    base = os.path.dirname(os.path.abspath(a.liste))
    plans = []
    for ligne in open(a.liste, encoding="utf-8"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        morceaux = ligne.rsplit(maxsplit=2)
        if len(morceaux) == 3 and all(m.replace(".", "", 1).isdigit() for m in morceaux[1:]):
            fichier, debut, duree = morceaux[0], float(morceaux[1]), float(morceaux[2])
        else:
            fichier, debut, duree = ligne, None, None
        plans.append((os.path.join(base, fichier), debut, duree))
    if not plans:
        raise SystemExit("liste vide : " + a.liste)
    with tempfile.TemporaryDirectory() as tmp:
        noms = []
        fps = cadence(plans[0][0])
        for i, (f, d, t) in enumerate(plans):
            nom = os.path.join(tmp, "plan_%03d.mp4" % i)
            plan_normalise(f, nom, d, t, fps=fps)
            noms.append(nom)
        concat = os.path.join(tmp, "concat.txt")
        with open(concat, "w", encoding="utf-8") as fl:
            fl.writelines("file '%s'\n" % n.replace("\\", "/") for n in noms)
        ffmpeg("-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", "-movflags", "+faststart", a.sortie)


def musique(a):
    """Remplace le son par une musique, ramenée à −14 LUFS, coupée à la longueur de l'image avec un
    fondu de sortie d'une seconde (le seul fondu permis : une musique qui s'arrête net sonne cassée)."""
    duree = float(sonder(a.video)["format"]["duration"])
    with tempfile.TemporaryDirectory() as tmp:
        brute = os.path.join(tmp, "musique.wav")
        # ⚠ UNE MUSIQUE PLUS COURTE QUE L'IMAGE BOUCLE (mesuré le 5 octobre 2026) : sans `-stream_loop`, `-shortest`
        # coupait la VIDÉO à la longueur de la musique, sans un mot — un devlog de 185 s sortait à 150 s, sans sa fin.
        ffmpeg("-stream_loop", "-1", "-ss", str(a.debut_musique), "-t", str(duree), "-i", a.musique,
               "-af", "afade=t=out:st=%.3f:d=1" % max(0.0, duree - 1.0), "-ar", "48000", "-ac", "2", brute)
        ffmpeg("-i", a.video, "-i", brute, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
               "-af", filtre_volume(brute), *AUDIO_YT, "-shortest", "-movflags", "+faststart", a.sortie)


def short(a):
    """Un Short : 1080 × 1920, recadré dans la hauteur de la source. `--centre` place la fenêtre
    (0 = bord gauche, 1 = bord droit) : on cadre l'action, jamais le milieu par défaut sans regarder."""
    filtre = ("scale=-2:1920:flags=lanczos:out_range=tv,crop=1080:1920:(iw-1080)*%f:0,setsar=1,"
              "format=yuv420p" % a.centre)
    if a_du_son(a.source):
        ffmpeg("-i", a.source, "-vf", filtre, *VIDEO_YT, *AUDIO_YT, a.sortie)
    else:
        ffmpeg("-i", a.source, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", filtre,
               "-shortest", *VIDEO_YT, *AUDIO_YT, a.sortie)


def planche(a):
    """Une image toutes les `pas` secondes, en grille, horodatée : on CHOISIT ses moments sur une
    planche, on ne les devine pas (la méthode de River Stones, `--reperer`)."""
    police = C.POLICES["texte"].replace("\\", "/").replace(":", "\\:")
    ffmpeg("-i", a.source, "-vf",
           "fps=1/%s,scale=384:-2,drawtext=fontfile='%s':text='%%{pts\\:hms}':x=8:y=8:fontsize=20:"
           "fontcolor=white:box=1:boxcolor=black@0.6,tile=6x6" % (a.pas, police),
           "-frames:v", "1", a.sortie)


def gif(a):
    """Un GIF qui se joue tout seul en arrivant dessus (r/godot, README, Discord, itch) — muet par nature.
    Palette calculée sur le clip lui-même : les 256 couleurs par défaut font des bandes dans l'eau et les
    dégradés. Boucle infinie. ⚠ Le poids monte vite : on garde 6-10 s, 15 images/s, 720 px de large."""
    entree = ["-ss", str(a.debut)] if a.debut else []
    if a.duree:
        entree += ["-t", str(a.duree)]
    filtre = ("fps=%s,scale=%d:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];"
              "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle" % (a.fps, a.largeur))
    ffmpeg(*entree, "-i", a.source, "-filter_complex", filtre, "-loop", "0", a.sortie)
    poids = os.path.getsize(a.sortie) / 1e6
    print("%s : %.1f Mo%s" % (os.path.basename(a.sortie), poids,
                              "  ÉCART : plus de %d Mo : raccourcir ou réduire" % a.max_mo if poids > a.max_mo else ""))


def verifier(a):
    """Le contrôle de sortie. Rend 1 au premier écart : une vidéo qui ne passe pas ne part pas."""
    info = sonder(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    son = [s for s in info["streams"] if s["codec_type"] == "audio"]
    attendu = (1080, 1920) if a.short else (1920, 1080)
    ecarts = []
    if (v["width"], v["height"]) != attendu:
        ecarts.append("taille %dx%d, attendu %dx%d" % (v["width"], v["height"], *attendu))
    if v["codec_name"] != "h264" or v.get("pix_fmt") != "yuv420p":
        ecarts.append("image %s/%s, attendu h264/yuv420p" % (v["codec_name"], v.get("pix_fmt")))
    if not son:
        ecarts.append("aucune piste son")
    elif son[0]["codec_name"] != "aac" or son[0]["sample_rate"] != "48000":
        ecarts.append("son %s %s Hz, attendu aac 48000" % (son[0]["codec_name"], son[0]["sample_rate"]))
    duree = float(info["format"]["duration"])
    if a.short and duree > 180:
        ecarts.append("Short de %.1f s, plus de 3 min" % duree)
    with open(a.video, "rb") as f:
        tete = f.read(4096)
    if b"moov" not in tete:
        ecarts.append("moov pas en tête (lecture en flux retardée) : refaire avec +faststart")
    if son:
        m = mesurer_volume(a.video)
        i = float(m["input_i"])
        if i > -60 and abs(i - LUFS) > 2:
            ecarts.append("volume %.1f LUFS, attendu %.0f ± 2" % (i, LUFS))
        print("son : %.1f LUFS intégrés, crête %.1f dBTP" % (i, float(m["input_tp"])))
    print("%s : %dx%d, %.1f s, %s" % (os.path.basename(a.video), v["width"], v["height"], duree,
                                      v.get("r_frame_rate")))
    for e in ecarts:
        print("ÉCART :", e)
    print("VERDICT :", "OK" if not ecarts else "REFUSÉ")
    raise SystemExit(1 if ecarts else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = p.add_subparsers(dest="commande", required=True)
    c = sp.add_parser("couper"); c.add_argument("source"); c.add_argument("sortie")
    c.add_argument("--debut", type=float); c.add_argument("--duree", type=float); c.set_defaults(f=couper)
    c = sp.add_parser("monter"); c.add_argument("liste"); c.add_argument("sortie"); c.set_defaults(f=monter)
    c = sp.add_parser("musique"); c.add_argument("video"); c.add_argument("musique"); c.add_argument("sortie")
    c.add_argument("--debut-musique", type=float, default=0.0); c.set_defaults(f=musique)
    c = sp.add_parser("short"); c.add_argument("source"); c.add_argument("sortie")
    c.add_argument("--centre", type=float, default=0.5); c.set_defaults(f=short)
    c = sp.add_parser("planche"); c.add_argument("source"); c.add_argument("sortie")
    c.add_argument("--pas", type=float, default=5); c.set_defaults(f=planche)
    c = sp.add_parser("gif"); c.add_argument("source"); c.add_argument("sortie")
    c.add_argument("--debut", type=float); c.add_argument("--duree", type=float, default=8)
    c.add_argument("--fps", type=float, default=15); c.add_argument("--largeur", type=int, default=720)
    c.add_argument("--max-mo", type=float, default=20); c.set_defaults(f=gif)
    c = sp.add_parser("verifier"); c.add_argument("video"); c.add_argument("--short", action="store_true")
    c.set_defaults(f=verifier)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
