# -*- coding: utf-8 -*-
"""LA VITRINE — d'une liste de pièces au lot prêt à téléverser, vérifié, et sa planche à JUGER.

    python -m publindie vitrine PROJET DESTINATION [--seulement NOM] [--planche-seule]

La liste vit dans `<studio>/PROJETS/<Projet>/06_boutique/<destination>/vitrine.json` :

    {
      "destination": "itch",
      "sortie": "06_boutique/itch/lot",                       # relatif au dossier du projet ; vidé de ses anciennes pièces
      "pieces": [
        {"role": "couverture", "nom": "cover", "source": "04_exports/trailer.mp4",
         "debut": 2.0, "duree": 4.0, "sorte": "gif", "largeur": 630, "hauteur": 500, "fps": 12},
        {"role": "capture", "nom": "01_interface", "source": "02_rushes/vitrine/interface.png"},
        {"role": "capture", "nom": "02_ile", "source": "04_exports/tour.mp4", "temps": 3.5, "recadrage": [290, 66, 1340, 1000]},
        {"role": "boucle", "nom": "tour", "source": "04_exports/tour.mp4", "debut": 0, "duree": 8}
      ]
    }

- `source` : relatif au dossier du projet (ou absolu). Une vidéo donne une IMAGE (`temps`), un GIF (`sorte: gif`) ou une
  BOUCLE (role `boucle`) ; une image reste une image.
- `recadrage` [x, y, l, h] en pixels de la source, AVANT la mise à l'échelle ; `largeur` / `hauteur` : la taille voulue
  (les deux : on remplit en coupant, centré sur `centre` [0..1, 0..1]) ; sans elles, la taille de la source.
- Le POIDS se tient tout seul sous la limite de la vitrine : la qualité JPEG baisse, le GIF perd des images par seconde
  puis de la largeur, la boucle monte son CRF — et le rapport dit ce qui a été cédé. Rien ne se dégrade sans être dit.

⚠ LE MÉDIA VIENT DU VRAI PRODUIT : ce module recadre et réduit, il ne retouche jamais une image (ni couleur, ni netteté).
⚠ LA PLANCHE (`<sortie>/planche.png`) montre chaque pièce telle que le visiteur la voit, avec son poids et son verdict :
on la REGARDE avant de téléverser (« ce qui se voit se juge à l'image »).
"""
import json
import os
import shutil
import subprocess
import tempfile

from publindie import chemins as C
from publindie import destinations as D

VIDEOS = (".mp4", ".mkv", ".avi", ".mov", ".webm")
IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
LARGEURS_SITE = (960, 1920, 2560)


# ── les outils ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _ffmpeg(*args):
    r = subprocess.run([C.OUTILS["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg a échoué :\n" + r.stderr[-1500:])


def _sonder(chemin):
    r = subprocess.run([C.OUTILS["ffprobe"], "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                        chemin], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffprobe ne lit pas %s" % chemin)
    info = json.loads(r.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    duree = float(info["format"].get("duration") or v.get("duration") or 0)
    return v["width"], v["height"], duree


def _mo(chemin):
    return os.path.getsize(chemin) / 1e6


def _taille_cible(piece, l_src, h_src):
    """(recadrage ffmpeg/PIL, largeur, hauteur) : le recadrage demandé, puis le remplissage du cadre voulu."""
    x, y, l, h = piece.get("recadrage") or (0, 0, l_src, h_src)
    lv, hv = piece.get("largeur"), piece.get("hauteur")
    if lv and hv:
        cible = lv / hv
        if l / h > cible:                      # trop large : on coupe sur les côtés
            nl = round(h * cible)
            cx = piece.get("centre", [0.5, 0.5])[0]
            x, l = x + round((l - nl) * cx), nl
        else:
            nh = round(l / cible)
            cy = piece.get("centre", [0.5, 0.5])[1]
            y, h = y + round((h - nh) * cy), nh
        return (x, y, l, h), lv, hv
    if lv:
        return (x, y, l, h), lv, round(h * lv / l / 2) * 2
    if hv:
        return (x, y, l, h), round(l * hv / h / 2) * 2, hv
    return (x, y, l, h), l, h


def _filtre(rec, l, h):
    x, y, lr, hr = rec
    return "crop=%d:%d:%d:%d,scale=%d:%d:flags=lanczos" % (lr, hr, x, y, l, h)


# ── les pièces ───────────────────────────────────────────────────────────────────────────────────────────────────────

def faire_image(piece, source, sortie_sans_ext, limite_mo, site=False):
    """Une image (d'une image ou d'une image de vidéo). JPEG (qualité 92 → 70 tant que le poids dépasse), ou, pour le
    site, WebP aux largeurs du site. Rend (fichiers, notes)."""
    from PIL import Image
    notes = []
    with tempfile.TemporaryDirectory() as tmp:
        if source.lower().endswith(VIDEOS):
            png = os.path.join(tmp, "image.png")
            _ffmpeg("-ss", str(piece.get("temps", 0)), "-i", source, "-frames:v", "1", png)
            source = png
        with Image.open(source) as brute:
            im = brute.convert("RGB")
        rec, l, h = _taille_cible(piece, *im.size)
        x, y, lr, hr = rec
        im = im.crop((x, y, x + lr, y + hr))
        if (l, h) != im.size:
            if l > im.size[0]:
                notes.append("AGRANDIE de %d à %d px de large : refaire la capture plus grande" % (im.size[0], l))
            im = im.resize((l, h), Image.LANCZOS)
        if site:
            faits = []
            for lw in LARGEURS_SITE:
                if lw > im.size[0]:
                    continue
                r = im if lw == im.size[0] else im.resize((lw, round(im.size[1] * lw / im.size[0])), Image.LANCZOS)
                f = "%s-%d.webp" % (sortie_sans_ext, lw)
                r.save(f, "WEBP", quality=86, method=6)
                faits.append(f)
            if not faits:
                notes.append("plus étroite que %d px : aucune déclinaison" % LARGEURS_SITE[0])
            return faits, notes
        f = sortie_sans_ext + ".jpg"
        for q in (92, 88, 84, 80, 76, 72, 70):
            try:
                im.save(f, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 88 else 2)
            except OSError:                       # certaines libjpeg refusent optimize + progressive sur une grande image
                im.save(f, "JPEG", quality=q, subsampling=0 if q >= 88 else 2)
            if not limite_mo or _mo(f) <= limite_mo:
                break
        if q < 92:
            notes.append("JPEG qualité %d pour tenir %g Mo" % (q, limite_mo))
        return [f], notes


def faire_gif(piece, source, sortie_sans_ext, limite_mo):
    """Un GIF qui boucle (palette calculée sur le clip, comme `video.gif`). Trop lourd : on cède d'abord des images par
    seconde (jusqu'à 8), puis de la largeur (par 10 %, jusqu'à 60 %) — et la note le dit."""
    l_src, h_src, _ = _sonder(source)
    rec, l, h = _taille_cible(piece, l_src, h_src)
    fps0 = piece.get("fps", 15)
    f = sortie_sans_ext + ".gif"
    essais = [(fps, 1.0) for fps in sorted({fps0, min(fps0, 12), min(fps0, 10), min(fps0, 8)}, reverse=True)]
    essais += [(min(fps0, 8), k / 10) for k in range(9, 5, -1)]
    entree = ["-ss", str(piece.get("debut", 0)), "-t", str(piece.get("duree", 6))]
    for fps, k in essais:
        lk, hk = round(l * k / 2) * 2, round(h * k / 2) * 2
        filtre = ("%s,fps=%s,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];"
                  "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle" % (_filtre(rec, lk, hk), fps))
        _ffmpeg(*entree, "-i", source, "-filter_complex", filtre, "-loop", "0", f)
        if not limite_mo or _mo(f) <= limite_mo:
            break
    notes = []
    if (fps, k) != essais[0]:
        notes.append("GIF cédé à %s img/s, %d × %d, pour tenir %g Mo" % (fps, lk, hk, limite_mo))
    if _mo(f) > (limite_mo or 1e9):
        notes.append("même réduit, le GIF dépasse : raccourcir le passage (`duree`)")
    return [f], notes


def faire_boucle(piece, source, sortie_sans_ext, limite_mo):
    """Une boucle muette pour le web : WebM (VP9) + MP4 (H.264, `moov` en tête) + image d'attente WebP. Le CRF monte
    tant que le plus lourd des deux dépasse la limite."""
    l_src, h_src, _ = _sonder(source)
    rec, l, h = _taille_cible(piece, l_src, h_src)
    entree = ["-ss", str(piece.get("debut", 0)), "-t", str(piece.get("duree", 8)), "-i", source]
    vf = _filtre(rec, l, h) + ",format=yuv420p"
    webm, mp4, poster = sortie_sans_ext + ".webm", sortie_sans_ext + ".mp4", sortie_sans_ext + ".webp"
    notes = []
    for i, (crf_vp9, crf_264) in enumerate(((32, 23), (36, 26), (40, 29), (44, 32))):
        _ffmpeg(*entree, "-vf", vf, "-an", "-c:v", "libvpx-vp9", "-crf", str(crf_vp9), "-b:v", "0", "-row-mt", "1",
                "-deadline", "good", "-cpu-used", "2", webm)
        _ffmpeg(*entree, "-vf", vf, "-an", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf",
                str(crf_264), "-movflags", "+faststart", mp4)
        if not limite_mo or max(_mo(webm), _mo(mp4)) <= limite_mo:
            break
    if limite_mo and max(_mo(webm), _mo(mp4)) > limite_mo:
        # le CRF ne suffit pas (une image très chargée : feuillage, eau, bruit) : un débit plafonné, 75 % du budget (VP9 en une passe déborde)
        kbits = int(limite_mo * 8000 * 0.75 / max(float(piece.get("duree", 8)), 0.5))
        _ffmpeg(*entree, "-vf", vf, "-an", "-c:v", "libvpx-vp9", "-b:v", "%dk" % kbits, "-maxrate", "%dk" % kbits,
                "-bufsize", "%dk" % (kbits * 2), "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", webm)
        _ffmpeg(*entree, "-vf", vf, "-an", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-b:v",
                "%dk" % kbits, "-maxrate", "%dk" % kbits, "-bufsize", "%dk" % (kbits * 2), "-movflags", "+faststart", mp4)
        notes.append("boucle plafonnée à %d kbit/s pour tenir %g Mo (image très chargée : la regarder)" % (kbits, limite_mo))
    elif i:
        notes.append("boucle compressée (CRF VP9 %d, H.264 %d) pour tenir %g Mo" % (crf_vp9, crf_264, limite_mo))
    _ffmpeg("-ss", str(piece.get("debut", 0)), "-i", source, "-frames:v", "1", "-vf", _filtre(rec, l, h),
            "-c:v", "libwebp", "-quality", "82", poster)
    return [webm, mp4, poster], notes


# ── le lot ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def _sorte(piece, source):
    if piece["role"] == "boucle":
        return "boucle"
    if piece.get("sorte") == "gif" or source.lower().endswith(".gif"):
        return "gif"
    return "image"


def charger(projet, destination):
    chemin = C.dossier_projet(projet, "06_boutique", destination, "vitrine.json")
    if not os.path.isfile(chemin):
        raise SystemExit("pas de liste : %s" % chemin)
    with open(chemin, encoding="utf-8") as f:
        v = json.load(f)
    v.setdefault("destination", destination)
    v.setdefault("sortie", os.path.join("06_boutique", destination, "lot"))
    return v


def mesurer(fichier):
    """(sorte, largeur, hauteur, Mo, secondes) d'un fichier produit."""
    ext = os.path.splitext(fichier)[1].lower()
    if ext in (".webm", ".mp4"):
        l, h, s = _sonder(fichier)
        return "boucle", l, h, _mo(fichier), s
    from PIL import Image
    with Image.open(fichier) as im:
        return ("gif" if ext == ".gif" else "image"), im.size[0], im.size[1], _mo(fichier), None


def fabriquer(projet, destination, seulement=None, sans_fabriquer=False):
    """Fabrique le lot, le vérifie, écrit `rapport.json` et `planche.png`. Rend (rapport, fautes)."""
    v = charger(projet, destination)
    base = C.dossier_projet(projet)
    sortie = os.path.join(base, v["sortie"])
    os.makedirs(sortie, exist_ok=True)
    rapport, fautes, comptes = [], [], {}
    for p in v["pieces"]:
        comptes[p["role"]] = comptes.get(p["role"], 0) + 1
        if seulement and p["nom"] != seulement:
            continue
        source = p["source"] if os.path.isabs(p["source"]) else os.path.join(base, p["source"])
        regle = D.piece(v["destination"], p["role"])
        sorte = _sorte(p, source)
        ligne = {"nom": p["nom"], "role": p["role"], "sorte": sorte, "source": p["source"], "fichiers": [], "notes": [],
                 "fautes": []}
        if not os.path.exists(source):
            ligne["fautes"].append("source absente : %s" % p["source"])
        else:
            cible = os.path.join(sortie, p["nom"])
            try:
                if sans_fabriquer:
                    faits = sorted(os.path.join(sortie, f) for f in os.listdir(sortie)
                                   if os.path.splitext(f)[0].split("-")[0] == p["nom"])
                    notes = []
                elif sorte == "boucle":
                    faits, notes = faire_boucle(p, source, cible, regle.get("mo"))
                elif sorte == "gif" and source.lower().endswith(VIDEOS):
                    faits, notes = faire_gif(p, source, cible, regle.get("mo"))
                elif sorte == "gif":
                    shutil.copyfile(source, cible + ".gif")
                    faits, notes = [cible + ".gif"], []
                else:
                    faits, notes = faire_image(p, source, cible, regle.get("mo"), site=v["destination"] == "site")
            except RuntimeError as e:
                faits, notes = [], []
                ligne["fautes"].append(str(e).splitlines()[0])
            ligne["notes"] = notes
            for k, f in enumerate(faits):
                if f.endswith(".webp") and sorte == "boucle":
                    continue                                    # l'image d'attente n'est pas une pièce
                s, l, h, mo, sec = mesurer(f)
                ligne["fichiers"].append({"fichier": os.path.relpath(f, base).replace("\\", "/"), "largeur": l,
                                          "hauteur": h, "mo": round(mo, 3), "secondes": sec})
                if v["destination"] == "site" and sorte == "image" and k < len(faits) - 1:
                    continue                                    # les déclinaisons plus petites : seule la grande juge
                ligne["fautes"] += D.verifier_piece(v["destination"], p["role"], s, l, h, mo, sec)
        rapport.append(ligne)
        fautes += ["%s : %s" % (p["nom"], x) for x in ligne["fautes"]]
    if not seulement:
        fautes += D.verifier_nombres(v["destination"], comptes)
    with open(os.path.join(sortie, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump({"destination": v["destination"], "pieces": rapport, "fautes": fautes}, f, ensure_ascii=False, indent=1)
    planche(base, sortie, rapport)
    return rapport, fautes


def planche(base, sortie, rapport, largeur_vignette=480):
    """Chaque pièce en vignette (l'image, ou l'image du milieu d'un GIF / d'une boucle), sa taille, son poids, son
    verdict. Trois colonnes."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        police = ImageFont.truetype(C.POLICES["texte"], 16)
    except OSError:
        police = ImageFont.load_default()
    cases = []
    for ligne in rapport:
        if not ligne["fichiers"]:
            cases.append((None, ligne))
            continue
        f = os.path.join(base, ligne["fichiers"][-1 if ligne["sorte"] != "boucle" else 0]["fichier"])
        try:
            if ligne["sorte"] == "boucle":
                with tempfile.TemporaryDirectory() as tmp:
                    png = os.path.join(tmp, "m.png")
                    _ffmpeg("-ss", str((ligne["fichiers"][0]["secondes"] or 0) / 2), "-i", f, "-frames:v", "1", png)
                    im = Image.open(png).convert("RGB")
            else:
                with Image.open(f) as brute:
                    if getattr(brute, "n_frames", 1) > 1:
                        brute.seek(brute.n_frames // 2)
                    im = brute.convert("RGB")
        except Exception:
            im = None
        cases.append((im, ligne))
    col, haut_texte = 3, 66
    h_case = round(largeur_vignette * 9 / 16) + haut_texte
    rangs = (len(cases) + col - 1) // col or 1
    feuille = Image.new("RGB", (col * (largeur_vignette + 12) + 12, rangs * (h_case + 12) + 12), (22, 23, 27))
    d = ImageDraw.Draw(feuille)
    for i, (im, ligne) in enumerate(cases):
        x, y = 12 + (i % col) * (largeur_vignette + 12), 12 + (i // col) * (h_case + 12)
        if im is not None:
            im.thumbnail((largeur_vignette, h_case - haut_texte))
            feuille.paste(im, (x, y))
        ok = not ligne["fautes"]
        fi = ligne["fichiers"][0] if ligne["fichiers"] else None
        t1 = "%s %s · %s" % ("✓" if ok else "✗", ligne["nom"], ligne["role"])
        t2 = ("%d × %d · %.2f Mo%s" % (fi["largeur"], fi["hauteur"], fi["mo"],
                                       " · %.1f s" % fi["secondes"] if fi.get("secondes") else "")) if fi else ""
        t3 = (ligne["fautes"] or ligne["notes"] or [""])[0][:70]
        yt = y + h_case - haut_texte + 4
        d.text((x, yt), t1, fill=(120, 220, 140) if ok else (240, 110, 100), font=police)
        d.text((x, yt + 20), t2, fill=(228, 228, 231), font=police)
        d.text((x, yt + 40), t3, fill=(242, 202, 121), font=police)
    feuille.save(os.path.join(sortie, "planche.png"))
