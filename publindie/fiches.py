# -*- coding: utf-8 -*-
"""LES FICHES DE PUBLICATION ET LE JOURNAL — ce qui part, où, avec quel texte, et ce qui est déjà parti.

UNE FICHE par publication (un média et ses déclinaisons), dans `<studio>/PROJETS/<Projet>/07_publication/fiches/<id>.json` :

    {
      "id": "monde_cartoon",
      "projet": "MarchingBlocks",
      "resume": "le monde cartoon, survol de 93 s",          # pour soi, jamais publié
      "medias": {                                            # chemins relatifs au dossier du projet
        "video": "04_exports/monde_cartoon.mp4",
        "gif": "04_exports/gif/monde_cartoon_tour.gif",
        "gif_x": "04_exports/gif/monde_cartoon_tour_x.gif"
      },
      "lien": "https://…",                                   # optionnel : remplace {lien} dans les textes
      "declarations": ["Music: …"],                          # IA, musique, modèles : ce qui DOIT être dit
      "reseaux": {
        "youtube":  {"media": "video", "titre": "…", "texte": "…", "tags": ["…"], "prevu": "2026-10-22"},
        "x":        {"media": "gif_x", "texte": "…", "premiere_reponse": "… {lien}", "prevu": "2026-10-21"},
        "mastodon": {"media": "gif", "texte": "…", "alt": "texte alternatif du média"},
        "reddit":   {"media": "gif", "communaute": "r/IndieDev", "titre": "…", "texte": "…"}
      }
    }

Le média d'un réseau est une CLÉ de `medias` ; sa SORTE (video, short, gif, image) se lit sur le nom de la clé
(`gif_x` → gif, `short_…` → short) ou sur l'extension.

LE JOURNAL (`07_publication/journal.json`) : {id: {réseau: {"date": "…", "url": "…"}}} — ce qui est posté. On le tient à
la main (`python -m publindie marquer …`) : aucune plateforme ne publie sans un humain derrière.
"""
import datetime
import json
import os
import subprocess

from publindie import chemins as C
from publindie import reseaux as R


def dossier(projet, *parties):
    return C.dossier_projet(projet, *parties)


def charger_fiches(projet):
    d = dossier(projet, "07_publication", "fiches")
    sortie = []
    if not os.path.isdir(d):
        return sortie
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            with open(os.path.join(d, f), encoding="utf-8") as h:
                fiche = json.load(h)
            fiche.setdefault("id", f[:-5])
            fiche.setdefault("projet", projet)
            sortie.append(fiche)
    return sortie


def chemin_journal(projet):
    return dossier(projet, "07_publication", "journal.json")


def charger_journal(projet):
    p = chemin_journal(projet)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def marquer(projet, ident, reseau, url="", date=None):
    """Note qu'une publication est partie sur un réseau. Écrit à côté puis remplace (jamais un journal à moitié)."""
    if reseau not in R.RESEAUX:
        raise KeyError("réseau inconnu : %s (connus : %s)" % (reseau, ", ".join(R.RESEAUX)))
    if ident not in {f["id"] for f in charger_fiches(projet)}:
        raise KeyError("fiche inconnue : %s/%s" % (projet, ident))
    j = charger_journal(projet)
    j.setdefault(ident, {})[reseau] = {"date": date or datetime.date.today().isoformat(), "url": url}
    p = chemin_journal(projet)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as h:
        json.dump(j, h, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(p + ".tmp", p)
    return j


def sorte_du_media(cle, chemin):
    base = cle.split("_")[0]
    if base in ("video", "short", "gif", "image"):
        return base
    ext = os.path.splitext(chemin)[1].lower()
    return {".gif": "gif", ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image"}.get(ext, "video")


def mesurer(chemin):
    """Poids (Mo), durée (s), largeur, hauteur d'un média — par ffprobe s'il est là, le poids seul sinon."""
    mo = os.path.getsize(chemin) / 1048576.0
    ffprobe = C.OUTILS.get("ffprobe", "")
    if not ffprobe or not os.path.exists(ffprobe) or chemin.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return mo, None, None, None
    try:
        s = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                       "stream=width,height:format=duration", "-of", "json", chemin],
                                      capture_output=True, text=True, timeout=60).stdout)
        flux = (s.get("streams") or [{}])[0]
        duree = s.get("format", {}).get("duration")
        return mo, float(duree) if duree not in (None, "N/A") else None, flux.get("width"), flux.get("height")
    except (OSError, ValueError, subprocess.SubprocessError):
        return mo, None, None, None


def textes(fiche, reseau):
    """Les textes d'un réseau, {lien} remplacé, les déclarations ajoutées au texte si le réseau a de la place."""
    t = dict(fiche["reseaux"][reseau])
    lien = fiche.get("lien", "")
    for k in ("texte", "titre", "premiere_reponse"):
        if isinstance(t.get(k), str):
            t[k] = t[k].replace("{lien}", lien)
    return t


def verifier(fiche, mesurer_medias=True):
    """Les fautes d'une fiche : médias absents, textes trop longs, médias refusés. Une liste vide : tout part."""
    fautes = []
    projet = fiche["projet"]
    medias = fiche.get("medias", {})
    mesures = {}
    for cle, rel in medias.items():
        p = dossier(projet, rel)
        if not os.path.isfile(p):
            fautes.append("média « %s » absent : %s" % (cle, rel))
        elif mesurer_medias:
            mesures[cle] = mesurer(p)
    for reseau, conf in fiche.get("reseaux", {}).items():
        if reseau not in R.RESEAUX:
            fautes.append("réseau inconnu : %s" % reseau)
            continue
        t = textes(fiche, reseau)
        fautes += R.verifier_texte(reseau, t.get("texte", ""), t.get("titre"))
        if t.get("premiere_reponse"):
            if R.longueur(t["premiere_reponse"], reseau) > R.RESEAUX[reseau]["texte"]:
                fautes.append("%s : première réponse trop longue" % R.RESEAUX[reseau]["nom"])
        cle = conf.get("media")
        if cle is None:
            continue
        if cle not in medias:
            fautes.append("%s : le média « %s » n'est pas dans la fiche" % (R.RESEAUX[reseau]["nom"], cle))
            continue
        if cle in mesures:
            mo, s, w, h = mesures[cle]
            fautes += R.verifier_media(reseau, sorte_du_media(cle, medias[cle]), mo, s, w, h)
        else:
            fautes += R.verifier_media(reseau, sorte_du_media(cle, medias[cle]))
    if fiche.get("reseaux", {}).get("reddit") and not fiche["reseaux"]["reddit"].get("communaute"):
        fautes.append("Reddit : dire la communauté (une seule par semaine au plus)")
    return fautes


def preparer(fiche):
    """La feuille de route d'une publication : `07_publication/a_poster/<id>.md`, un bloc par réseau (le fichier à
    joindre, le texte à coller, ce qui est déjà parti). Aucun média n'est recopié."""
    projet = fiche["projet"]
    j = charger_journal(projet).get(fiche["id"], {})
    lignes = ["# À poster : %s (%s)" % (fiche["id"], projet), ""]
    if fiche.get("resume"):
        lignes += [fiche["resume"], ""]
    fautes = verifier(fiche)
    if fautes:
        lignes += ["⚠ **À CORRIGER AVANT DE POSTER :**", ""] + ["- " + f for f in fautes] + [""]
    if fiche.get("declarations"):
        lignes += ["**À déclarer partout :** " + " · ".join(fiche["declarations"]), ""]
    for reseau in R.RESEAUX:
        if reseau not in fiche.get("reseaux", {}):
            continue
        t = textes(fiche, reseau)
        fait = j.get(reseau)
        etat = "✓ posté le %s %s" % (fait["date"], fait.get("url", "")) if fait else "à poster" + (
            " le %s" % t["prevu"] if t.get("prevu") else "")
        lignes += ["## %s — %s" % (R.RESEAUX[reseau]["nom"], etat), ""]
        if t.get("media"):
            lignes.append("Fichier : `%s`" % dossier(projet, fiche["medias"].get(t["media"], "?")).replace("\\", "/"))
        if t.get("communaute"):
            lignes.append("Communauté : %s" % t["communaute"])
        for k, nom in (("titre", "Titre"), ("texte", "Texte"), ("premiere_reponse", "Première réponse"),
                       ("alt", "Texte alternatif")):
            if t.get(k):
                lignes += ["", "%s :" % nom, "```", t[k], "```"]
        if t.get("tags"):
            lignes += ["", "Tags : " + ", ".join(t["tags"])]
        lignes.append("")
    p = dossier(projet, "07_publication", "a_poster", fiche["id"] + ".md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as h:
        h.write("\n".join(lignes))
    return p, fautes


def calendrier(projets, depuis=None, jours=14):
    """Ce qui est PRÉVU (champ `prevu` de chaque réseau), jour par jour, tous projets — et ce qui est déjà parti."""
    depuis = depuis or datetime.date.today()
    fin = depuis + datetime.timedelta(days=jours)
    par_jour = {}
    for projet in projets:
        j = charger_journal(projet)
        for f in charger_fiches(projet):
            for reseau, conf in f.get("reseaux", {}).items():
                if not conf.get("prevu"):
                    continue
                d = datetime.date.fromisoformat(conf["prevu"])
                if depuis <= d < fin:
                    fait = reseau in j.get(f["id"], {})
                    par_jour.setdefault(d, []).append((projet, f["id"], reseau, fait))
    return dict(sorted(par_jour.items()))
