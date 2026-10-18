# -*- coding: utf-8 -*-
"""LA CAPTURE D'UNE FENÊTRE — ce que le produit ne sait pas filmer lui-même (Jordan à la souris, des heures).

    python -m publindie.capture demarrer DOSSIER --exe MarchingBlocks [--fps 10]
    python -m publindie.capture etat     DOSSIER
    python -m publindie.capture arreter  DOSSIER
    python -m publindie.capture accelerer DOSSIER SORTIE.mp4 --duree 240     # le timelapse

⚠ ffmpeg `gfxcapture` (Windows Graphics Capture, ffmpeg 8.1) filme UNE fenêtre, même recouverte : ce que Jordan
ouvre par-dessus (un navigateur, un message) n'entre pas dans la vidéo — gdigrab sur le bureau l'aurait pris.
⚠ PAR TRANCHES DE 10 MIN en MKV : un arrêt brutal (ou un plantage) ne perd que la tranche en cours, pas la séance.
⚠ 10 IMAGES/S SUFFISENT pour un timelapse : trois heures de construction ramenées à quatre minutes gardent une
image sur quinze à 10 images/s. Le curseur de Windows est filmé (on voit où Jordan travaille).
"""
import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import time

from publindie import chemins as C

ETAT = "capture.json"


def demarrer(a):
    os.makedirs(a.dossier, exist_ok=True)
    etat = os.path.join(a.dossier, ETAT)
    if os.path.exists(etat):
        raise SystemExit("une capture tourne déjà ici (%s) — `arreter` d'abord" % etat)
    seance = "seance_%02d" % (len({os.path.basename(f).split("_")[1] for f in glob.glob(os.path.join(a.dossier, "seance_*.mkv"))}) + 1)
    source = "gfxcapture=window_exe='(?i)%s':max_framerate=%d:capture_cursor=1:width=-2:height=-2" % (a.exe, a.fps)
    commande = [C.OUTILS["ffmpeg"], "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", source,
                "-vf", "hwdownload,format=bgra,fps=%d,format=yuv420p" % a.fps,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", str(a.fps * 10),
                "-f", "segment", "-segment_time", "600", "-reset_timestamps", "1",
                os.path.join(a.dossier, seance + "_%03d.mkv")]
    journal = open(os.path.join(a.dossier, seance + ".log"), "w", encoding="utf-8")
    p = subprocess.Popen(commande, stdin=subprocess.DEVNULL, stdout=journal, stderr=journal,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    json.dump({"pid": p.pid, "seance": seance, "commande": commande}, open(etat, "w", encoding="utf-8"), indent=1)
    print("capture %s lancée (pid %d) -> %s" % (seance, p.pid, a.dossier))


def etat(a):
    chemin = os.path.join(a.dossier, ETAT)
    if not os.path.exists(chemin):
        print("aucune capture en cours")
        return
    e = json.load(open(chemin, encoding="utf-8"))
    vivant = subprocess.run(["tasklist", "/FI", "PID eq %d" % e["pid"]], capture_output=True, text=True).stdout
    tranches = sorted(glob.glob(os.path.join(a.dossier, e["seance"] + "_*.mkv")))
    taille = sum(os.path.getsize(f) for f in tranches) / 1e6
    print("%s : %s, %d tranche(s), %.0f Mo" % (e["seance"], "EN COURS" if str(e["pid"]) in vivant else "ARRÊTÉE",
                                              len(tranches), taille))
    log = os.path.join(a.dossier, e["seance"] + ".log")
    if os.path.exists(log) and os.path.getsize(log):
        print("journal :", open(log, encoding="utf-8", errors="replace").read()[-600:])


def arreter(a):
    chemin = os.path.join(a.dossier, ETAT)
    if not os.path.exists(chemin):
        raise SystemExit("aucune capture en cours ici")
    e = json.load(open(chemin, encoding="utf-8"))
    # Ctrl+Break au groupe : ffmpeg ferme proprement la tranche en cours ; sinon on tue (la tranche MKV reste lisible).
    # ⚠ ON ATTEND qu'il ferme (mesuré le 5 octobre 2026 : tué tout de suite, la tranche restait illisible, son en-tête
    # jamais écrit). Dix secondes, puis on force.
    try:
        os.kill(e["pid"], signal.CTRL_BREAK_EVENT)
    except OSError:
        pass
    for i in range(20):
        if str(e["pid"]) not in subprocess.run(["tasklist", "/FI", "PID eq %d" % e["pid"]],
                                                capture_output=True, text=True).stdout:
            break
        time.sleep(0.5)
    else:
        subprocess.run(["taskkill", "/F", "/PID", str(e["pid"]), "/T"], capture_output=True)
    os.remove(chemin)
    print("capture %s arrêtée" % e["seance"])


def accelerer(a):
    """Toutes les tranches, dans l'ordre, ramenées à `--duree` secondes à 30 images/s, en 1920 × 1080."""
    tranches = sorted(glob.glob(os.path.join(a.dossier, "seance_*.mkv")))
    if not tranches:
        raise SystemExit("aucune tranche dans " + a.dossier)
    liste = os.path.join(a.dossier, "tranches.txt")
    with open(liste, "w", encoding="utf-8") as f:
        f.writelines("file '%s'\n" % os.path.abspath(t).replace("\\", "/") for t in tranches)
    total = 0.0
    for t in tranches:
        r = subprocess.run([C.OUTILS["ffprobe"], "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", t],
                           capture_output=True, text=True)
        total += float(r.stdout.strip() or 0)
    facteur = max(1.0, total / a.duree)
    print("%d tranche(s), %.0f min filmées -> %.0f s : x%.1f" % (len(tranches), total / 60, a.duree, facteur))
    subprocess.run([C.OUTILS["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", liste, "-vf",
                    "setpts=PTS/%f,fps=30,scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
                    "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p" % facteur,
                    "-an", "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-movflags", "+faststart", a.sortie],
                   check=True)
    print("timelapse -> " + a.sortie)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(required=True)
    c = sp.add_parser("demarrer"); c.add_argument("dossier"); c.add_argument("--exe", required=True)
    c.add_argument("--fps", type=int, default=10); c.set_defaults(f=demarrer)
    c = sp.add_parser("etat"); c.add_argument("dossier"); c.set_defaults(f=etat)
    c = sp.add_parser("arreter"); c.add_argument("dossier"); c.set_defaults(f=arreter)
    c = sp.add_parser("accelerer"); c.add_argument("dossier"); c.add_argument("sortie")
    c.add_argument("--duree", type=float, default=240); c.set_defaults(f=accelerer)
    a = p.parse_args()
    a.f(a)
