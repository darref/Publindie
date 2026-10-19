# -*- coding: utf-8 -*-
"""L'ALIGNEMENT — la règle de `SpannerGames/CLAUDE.md` §0 (Jordan, 19 octobre 2026), en une commande, SUR LE PC.

    python -m publindie aligner                       # tout : pousser, exporter ce qui a changé, itch.io, Publindie, le site
    python -m publindie aligner --etapes pousser,site # seulement ces étapes
    python -m publindie aligner --commiter Pix WaterDrop   # commite aussi le travail en cours de ces dépôts
    python -m publindie aligner --forcer SoluTiles    # réexporte même si le commit n'a pas bougé
    python -m publindie aligner --essai               # dit ce qu'il ferait, ne touche à rien
    python -m publindie aligner --etapes exporter --seulement SoluTiles   # un seul projet

Ce que dit `publindie.json` (clé `alignement`) : les dépôts, les exports de chaque projet (presets Godot ou commande du
projet), le site. Le rapport s'écrit dans `<studio>/ATELIER/alignement/<date>.md`, et la liste des LIVRABLES à rapatrier
sur le téléphone dans `ATELIER/alignement/livrables.json` (`OUTILS/rapatrier.sh` la lit).

⚠ CE QUE LA COMMANDE NE DÉCIDE PAS SEULE : commiter le travail en cours d'un dépôt (il faut le nommer dans `--commiter` :
une autre session y travaille peut-être — `ListAgents` d'abord) ; fusionner une branche ; monter une version. Elle POUSSE
ce qui est commité, TIRE ce qui est en avance sur GitHub (avance rapide seulement), EXPORTE ce dont le commit a bougé.
⚠ UN EXPORT QUI ÉCHOUE EST DIT, pas réessayé ; les autres continuent.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

from publindie import chemins as C

BASH = r"C:/Program Files/Git/bin/bash.exe"


def _conf():
    with open(C.CONFIG, encoding="utf-8") as f:
        return json.load(f).get("alignement", {})


def git(depot, *args, verifier=False):
    r = subprocess.run(["git", "-C", depot, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if verifier and r.returncode != 0:
        raise RuntimeError("git %s : %s" % (" ".join(args), (r.stderr or r.stdout).strip()[-400:]))
    return r.stdout.strip()


# ── 1. pousser ───────────────────────────────────────────────────────────────────────────────────────────────────────

def etat_depot(depot):
    e = {"branche": git(depot, "branch", "--show-current"), "sale": [l for l in git(depot, "status", "--porcelain")
                                                                     .splitlines() if l.strip()]}
    e["amont"] = git(depot, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") or None
    if e["amont"] and "fatal" not in e["amont"]:
        git(depot, "fetch", "-q", e["amont"].split("/")[0])
        compte = git(depot, "rev-list", "--left-right", "--count", "HEAD...@{u}").split()
        e["avance"], e["retard"] = (int(compte[0]), int(compte[1])) if len(compte) == 2 else (0, 0)
    else:
        e["amont"], e["avance"], e["retard"] = None, 0, 0
    return e


def pousser(depots, commiter=(), essai=False, date=None):
    lignes = []
    for nom, depot in depots.items():
        if not os.path.isdir(os.path.join(depot, ".git")):
            lignes.append((nom, "absent", "pas de dépôt git en %s" % depot))
            continue
        try:
            e = etat_depot(depot)
            fait = []
            if e["sale"] and nom in commiter:
                if not essai:
                    git(depot, "add", "-A", verifier=True)
                    git(depot, "commit", "-q", "-m", "Alignement du %s : travail en cours commité (%d fichier(s))"
                        % (date, len(e["sale"])), verifier=True)
                fait.append("%d fichier(s) commité(s)" % len(e["sale"]))
                e = etat_depot(depot) if not essai else e
            if e["retard"] and not e["sale"]:
                if not essai:
                    git(depot, "merge", "--ff-only", "-q", "@{u}", verifier=True)
                fait.append("%d commit(s) tiré(s)" % e["retard"])
            elif e["retard"]:
                fait.append("⚠ %d commit(s) en retard sur %s, NON tirés (travail en cours)" % (e["retard"], e["amont"]))
            if e["avance"]:
                if not essai:
                    git(depot, "push", "-q", verifier=True)
                fait.append("%d commit(s) poussé(s) vers %s" % (e["avance"], e["amont"]))
            if not e["amont"]:
                fait.append("sans amont (le PC fait foi)")
            if e["sale"] and nom not in commiter:
                fait.append("⚠ %d fichier(s) non commité(s), laissés (--commiter %s pour les prendre)" % (len(e["sale"]), nom))
            lignes.append((nom, e["branche"], " · ".join(fait) or "à jour"))
        except RuntimeError as x:
            lignes.append((nom, "BLOQUÉ", str(x)))
    return lignes


# ── 2. exporter ──────────────────────────────────────────────────────────────────────────────────────────────────────

def presets(depot):
    """{nom du preset: export_path absolu} lus dans export_presets.cfg."""
    chemin = os.path.join(depot, "export_presets.cfg")
    sortie, nom = {}, None
    if not os.path.isfile(chemin):
        return sortie
    for l in open(chemin, encoding="utf-8", errors="replace"):
        m = re.match(r'^name="(.*)"', l)
        if m:
            nom = m.group(1)
        m = re.match(r'^export_path="(.*)"', l)
        if m and nom:
            p = m.group(1)
            sortie[nom] = os.path.normpath(p if os.path.isabs(p) or re.match(r"^[A-Za-z]:", p) else os.path.join(depot, p))
            nom = None
    return sortie


def version(depot):
    pg = os.path.join(depot, "project.godot")
    if os.path.isfile(pg):
        m = re.search(r'^config/version="(.*)"', open(pg, encoding="utf-8", errors="replace").read(), re.M)
        if m:
            return m.group(1)
    return ""


def _dernier(atelier):
    f = os.path.join(atelier, "DERNIER_EXPORT.txt")
    if os.path.isfile(f):
        try:
            return json.load(open(f, encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def editeur_ouvert(depot):
    """Le pid d'un Godot dont la ligne de commande nomme ce projet (un éditeur ouvert dessus), ou None."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name like 'Godot%'\" | ForEach-Object "
                        "{ \"$($_.ProcessId)`t$($_.CommandLine)\" }"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    cible = os.path.normcase(os.path.normpath(depot))
    for l in r.stdout.splitlines():
        pid, _, ligne = l.partition("\t")
        if cible in os.path.normcase(ligne.replace("/", "\\")) and "--headless" not in ligne:
            return pid
    return None


def exporter(depots, exports, forcer=(), essai=False, date=None, seulement=()):
    lignes, livrables = [], []
    for nom, regle in exports.items():
        if seulement and nom not in seulement:
            continue
        depot = depots.get(nom)
        atelier = os.path.join(C.RACINE, regle["atelier"])
        if not depot or not os.path.isdir(depot):
            lignes.append((nom, "absent", ""))
            continue
        commit = git(depot, "rev-parse", "--short", "HEAD")
        avant = _dernier(atelier)
        if avant.get("commit") == commit and nom not in forcer:
            lignes.append((nom, "à jour", "commit %s déjà exporté le %s" % (commit, avant.get("date", "?"))))
            livrables += avant.get("sorties", [])
            continue
        ouvert = editeur_ouvert(depot)
        if ouvert:
            lignes.append((nom, "sauté", "un Godot a ce projet ouvert (pid %s) : l'export réimporte le projet ; il partira "
                                         "au prochain alignement" % ouvert))
            continue
        if essai:
            lignes.append((nom, "à exporter", "commit %s (dernier : %s)" % (commit, avant.get("commit", "jamais"))))
            continue
        os.makedirs(atelier, exist_ok=True)
        debut = time.time()
        journal = os.path.join(atelier, "alignement_export.log")
        sorties, fautes = [], []
        with open(journal, "w", encoding="utf-8") as j:
            if "commande" in regle:
                cmd = [BASH if regle["commande"][0] == "bash" else regle["commande"][0], *regle["commande"][1:]]
                r = subprocess.run(cmd, cwd=depot, stdout=j, stderr=subprocess.STDOUT, timeout=regle.get("delai", 5400))
                if r.returncode != 0:
                    fautes.append("la commande a rendu %d (journal : %s)" % (r.returncode, journal))
                v = version(depot)
                for motif in regle.get("sorties", []):
                    for d in glob.glob(os.path.join(C.RACINE, regle["atelier"], motif.format(version=v))):
                        sorties += [f for f in glob.glob(os.path.join(d, "*")) if os.path.isfile(f)]
            else:
                chemins = presets(depot)
                for p in regle["presets"]:
                    if p not in chemins:
                        fautes.append("preset « %s » absent de export_presets.cfg" % p)
                        continue
                    os.makedirs(os.path.dirname(chemins[p]), exist_ok=True)
                    r = subprocess.run([C.OUTILS["godot"], "--headless", "--path", depot, "--export-release", p,
                                        chemins[p]], stdout=j, stderr=subprocess.STDOUT, timeout=regle.get("delai", 1800))
                    exe = chemins[p]
                    if r.returncode != 0 or not os.path.isfile(exe) or os.path.getmtime(exe) < debut:
                        fautes.append("« %s » : rien de neuf en %s (code %d, journal : %s)" % (p, exe, r.returncode, journal))
                        continue
                    sorties += [f for f in glob.glob(os.path.join(os.path.dirname(exe), "*"))
                                if os.path.isfile(f) and os.path.getmtime(f) >= debut]
        if fautes:
            lignes.append((nom, "ÉCHEC", " ; ".join(fautes)))
            continue
        rel = [os.path.relpath(f, C.RACINE).replace("\\", "/") for f in sorties]
        json.dump({"date": date, "commit": commit, "version": version(depot), "sorties": rel},
                  open(os.path.join(atelier, "DERNIER_EXPORT.txt"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        mo = sum(os.path.getsize(f) for f in sorties) / 1e6
        lignes.append((nom, "exporté", "commit %s, %d fichier(s), %.0f Mo, en %d s" % (commit, len(sorties), mo,
                                                                                       time.time() - debut)))
        livrables += rel
    return lignes, livrables


# ── 2 bis. itch.io ───────────────────────────────────────────────────────────────────────────────────────────────────

BUTLER = r"C:/Users/jorda/butler/butler.exe"


def itch(regles, exports, essai=False, date=None):
    """Pousse sur itch.io (butler) les exports NEUFS : un projet part quand le commit de son dernier export n'est pas celui
    de son dernier envoi (`ATELIER/<P>/builds/DERNIER_ITCH.txt`). Un canal `payant` ne part que si sa `garde` (un fichier
    de la sortie) ne contient plus « COMPL » (les blancs [À COMPLÉTER] du contrat).
    ⚠ butler ne coche pas « This file is a demo » : un canal neuf se règle UNE FOIS sur le web (la case reste ensuite)."""
    lignes = []
    butler = C.OUTILS.get("butler", BUTLER)
    for nom, r in regles.items():
        if nom.startswith("_"):
            continue                                            # une note, pas un projet
        atelier = os.path.join(C.RACINE, exports[nom]["atelier"])
        exp = _dernier(atelier)
        f_itch = os.path.join(atelier, "DERNIER_ITCH.txt")
        avant = json.load(open(f_itch, encoding="utf-8")) if os.path.isfile(f_itch) else {}
        if not exp.get("commit"):
            lignes.append((nom, "rien", "jamais exporté par l'alignement"))
            continue
        if avant.get("commit") == exp["commit"]:
            lignes.append((nom, "à jour", "le commit %s est déjà sur itch (%s)" % (exp["commit"], avant.get("date", "?"))))
            continue
        v = exp.get("version", "")
        partis, fautes = [], []
        for page, canaux in r["pages"].items():
            for canal, c in canaux.items():
                c = c if isinstance(c, dict) else {"chemin": c}
                chemin = os.path.join(atelier, c["chemin"].format(version=v))
                if c.get("garde"):
                    g = os.path.join(atelier, c["garde"].format(version=v))
                    if not os.path.isfile(g) or "COMPL" in open(g, encoding="utf-8", errors="replace").read():
                        lignes.append((nom, "retenu", "%s:%s — le contrat a encore des blancs (%s)" % (page, canal, g)))
                        continue
                if not os.path.exists(chemin):
                    fautes.append("%s:%s — %s absent" % (page, canal, chemin))
                    continue
                if essai:
                    partis.append("%s:%s" % (page, canal))
                    continue
                p = subprocess.run([butler, "push", chemin, "%s:%s" % (page, canal), "--userversion", v],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
                if p.returncode != 0:
                    fautes.append("%s:%s — butler : %s" % (page, canal, (p.stderr or p.stdout).strip()[-200:]))
                else:
                    partis.append("%s:%s" % (page, canal))
        if fautes:
            lignes.append((nom, "ÉCHEC", " ; ".join(fautes)))
        if partis:
            lignes.append((nom, "à pousser (essai)" if essai else "poussé", "%s en %s" % (", ".join(partis), v)))
        if not essai and not fautes and partis:
            json.dump({"date": date, "commit": exp["commit"], "version": v, "canaux": partis},
                      open(f_itch, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return lignes


# ── 3. Publindie ─────────────────────────────────────────────────────────────────────────────────────────────────────

def publindie_a_faire(depuis_jours=7):
    from publindie import fiches as FI
    from publindie import rangement as RG
    lignes = []
    for p in C.PROJETS:
        try:
            r = RG.rapport(p)
        except Exception as x:
            lignes.append((p, "ranger", "erreur : %s" % x))
            continue
        if r.get("absent"):
            continue
        if r["orphelins"]:
            lignes.append((p, "exports sans fiche", "%d (ex. %s)" % (len(r["orphelins"]), r["orphelins"][0])))
        if r["cites_absents"]:
            lignes.append((p, "cités absents", ", ".join(r["cites_absents"][:3])))
        for f in FI.charger_fiches(p):
            fautes = FI.verifier(f, True)
            if fautes:
                lignes.append((p, "fiche %s" % f["id"], fautes[0]))
    cal = FI.calendrier(list(C.PROJETS), None, depuis_jours)
    for d, items in cal.items():
        for projet, ident, reseau, fait in items:
            if not fait:
                lignes.append((projet, "à poster le %s" % d.isoformat(), "%s sur %s" % (ident, reseau)))
    return lignes


def medias_neufs(depuis):
    """Les GIF, Shorts, vidéos et lots de vitrine produits depuis `depuis` (horodatage) : ce qui part sur le téléphone."""
    sortie = []
    # ⚠ PAS LES VIDÉOS LONGUES : avec elles, 135 fichiers et 7 Go partaient sur le téléphone (mesuré le 19 octobre 2026).
    for motif in ("PROJETS/*/04_exports/**/*.gif", "PROJETS/*/04_exports/shorts/*.mp4", "PROJETS/*/06_boutique/*/lot/*",
                  "PROJETS/*/05_miniatures/*.png"):
        for f in glob.glob(os.path.join(C.RACINE, motif), recursive=True):
            if os.path.isfile(f) and os.path.getmtime(f) > depuis and os.path.getsize(f) < 60e6:
                sortie.append(os.path.relpath(f, C.RACINE).replace("\\", "/"))
    return sorted(sortie)


# ── 4. le site ───────────────────────────────────────────────────────────────────────────────────────────────────────

def site(regle, essai=False):
    depot, port = regle["depot"], regle.get("port", 8790)
    if essai:
        return [("site", "à construire", "puis l'aperçu sur le port %d" % port)]
    r = subprocess.run(["python", "outils/construire.py"], cwd=depot, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    fin = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    if r.returncode != 0:
        return [("site", "ÉCHEC de construction", fin[0])]
    p = subprocess.run(["python", "outils/construire.py", "--production"], cwd=depot, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    bloque = "prêt pour la production" if p.returncode == 0 else "--production refuse encore : %s" % (
        (p.stdout + p.stderr).strip().splitlines()[-1:] or ["?"])[0]
    subprocess.run(["python", "outils/construire.py"], cwd=depot, capture_output=True)   # --production a pu écrire public/
    # L'aperçu doit survivre à la session SSH : un processus créé par WMI échappe au « job » d'OpenSSH (qui tue tout à
    # la déconnexion). L'ancien serveur, s'il écoute encore, est arrêté d'abord.
    ps = ("Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction SilentlyContinue | ForEach-Object "
          "{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; "
          "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='\"%s\" -m http.server "
          "%d -d public'; CurrentDirectory='%s'} | Out-Null" % (port, sys.executable, port, depot.replace("/", "\\")))
    # ⚠ un processus créé par WMI n'a pas le PATH de l'utilisateur : `python` seul n'y est pas trouvé (vu le 19 octobre
    # 2026, l'aperçu ne répondait pas) — d'où le chemin complet de l'interpréteur.
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    time.sleep(4)
    ok = subprocess.run(["powershell", "-NoProfile", "-Command",
                         "(Invoke-WebRequest -UseBasicParsing http://localhost:%d/).StatusCode" % port],
                        capture_output=True, text=True).stdout.strip() == "200"
    return [("site", "construit", fin[0]), ("site", "production", bloque),
            ("site", "aperçu", ("en ligne sur le port %d (téléphone : ssh -L %d:localhost:%d pcjordan)" % (port, port, port))
             if ok else "⚠ l'aperçu ne répond pas sur le port %d" % port)]


# ── tout ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

def aligner(etapes=("pousser", "exporter", "itch", "publindie", "site"), commiter=(), forcer=(), essai=False, seulement=()):
    conf = _conf()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    dossier = os.path.join(C.RACINE, "ATELIER", "alignement")
    os.makedirs(dossier, exist_ok=True)
    trace = os.path.join(dossier, "dernier.json")
    rapport, livrables = [], []
    if "pousser" in etapes:
        rapport.append(("1. Pousser", pousser(conf["depots"], commiter, essai, date[:10])))
    if "exporter" in etapes:
        l, livrables = exporter(conf["depots"], conf.get("exports", {}), forcer, essai, date, seulement)
        rapport.append(("2. Exporter", l))
    if "itch" in etapes and conf.get("itch"):
        rapport.append(("2 bis. itch.io", itch(conf["itch"], conf.get("exports", {}), essai, date)))
    if "publindie" in etapes:
        rapport.append(("3. Publindie", publindie_a_faire()))
    if "site" in etapes and conf.get("site"):
        rapport.append(("4. Le site", site(conf["site"], essai)))
    # LA LISTE DES LIVRABLES NE DÉPEND PAS DES ÉTAPES LANCÉES : le dernier export de CHAQUE projet (son DERNIER_EXPORT.txt)
    # et les médias neufs depuis le dernier alignement COMPLET. Un alignement partiel (le site seul) l'effaçait (vu le 19 octobre 2026) ; le
    # téléphone ne recopie pas un fichier de même taille, donc rien ne part deux fois.
    livrables = sorted({f for r in conf.get("exports", {}).values()
                        for f in _dernier(os.path.join(C.RACINE, r["atelier"])).get("sorties", [])} | set(livrables))
    precedent = json.load(open(trace, encoding="utf-8")) if os.path.isfile(trace) else {}
    neufs = medias_neufs(precedent.get("horodatage", time.time() - 7 * 86400))
    texte = ["# Alignement du %s%s" % (date, " (ESSAI : rien n'a été touché)" if essai else ""), ""]
    for titre, lignes in rapport:
        texte += ["## " + titre, ""] + ["- **%s** — %s : %s" % l for l in lignes] + [""]
    texte += ["## Livrables à rapatrier", "", "%d fichier(s) d'export, %d média(s) neuf(s) depuis le dernier alignement complet"
              % (len(livrables), len(neufs)), ""]
    if not essai:
        with open(os.path.join(dossier, date[:10] + ".md"), "w", encoding="utf-8") as f:
            f.write("\n".join(texte))
        json.dump({"date": date, "exports": livrables, "medias": neufs},
                  open(os.path.join(C.RACINE, conf.get("livrables", "ATELIER/alignement/livrables.json")), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
        if set(etapes) >= {"pousser", "exporter", "itch", "publindie", "site"}:      # seul un alignement COMPLET fait date
            json.dump({"date": date, "horodatage": time.time()}, open(trace, "w", encoding="utf-8"))
    print("\n".join(texte))
    bloques = sum(1 for _, ls in rapport for l in ls if l[1] in ("BLOQUÉ", "ÉCHEC", "ÉCHEC de construction"))
    return 1 if bloques else 0
