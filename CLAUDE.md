# Publindie — charte

Les outils de publication de SpannerGames, devenus un projet à part (Jordan, 18 octobre 2026 : « améliore les outils de
publication et le rangement de ses sources et de ses exports comme un projet à part, et trouve-lui un nom d'app stylé
qui contient indie et publi ou post »). Statuts comme ailleurs : DÉCIDÉ · PROPOSÉ · MESURÉ · OUVERT.

## Ce qui est décidé ou proposé

- **LE NOM : Publindie — PROPOSÉ (Claude, 18 octobre 2026)** : « publier » + « indie ». « Indiepost » est pris (un
  magazine) ; « Publindie » ne ressortait nulle part (une recherche, pas un dépôt de marque). Renommer coûte peu tant
  que rien n'est public.
- **LE CODE ICI, LES MÉDIAS CHEZ LE STUDIO — PROPOSÉ.** Aucun média dans ce dépôt (`.gitignore`), jamais de LFS (Jordan,
  18 octobre 2026 : « il faut économiser le LFS, je suis à 90 % »). Le studio est décrit par son `publindie.json`
  (projets, outils, polices, marque, teintes).
- **`SpannerGames/OUTILS` NE CONTIENT PLUS QUE DES RELAIS** pour `chemins`, `video`, `miniature`, `voix`, `capture`,
  `chaine` : les ~37 scripts qui les appellent marchent tels quels. On modifie ICI, jamais le relais.
  `alleger_glb.py` et `remplacer_feuillage.py` (des outils 3D, pas de publication) restent dans `OUTILS`.
- **UNE FICHE PAR PUBLICATION** (`PROJETS/<P>/07_publication/fiches/<id>.json`) : les médias, les textes par réseau, les
  déclarations (IA, musique, modèles), la date prévue. **Le journal** (`journal.json`) dit ce qui est parti.
  `preparer` écrit la feuille de route (`a_poster/<id>.md`) sans recopier un seul média.
- **LES LIMITES DES RÉSEAUX VIVENT DANS `reseaux.py`** — relevées le 18 octobre 2026 sur des guides de tiers, À
  REVÉRIFIER sur les centres d'aide ; la plus petite valeur annoncée quand ils divergent.
- **PUBLINDIE NE PUBLIE PAS** : les plateformes n'ont pas d'API ouverte pour tout (itch, les annonces Steam) ou la font
  payer (X), et un humain publie. Il PRÉPARE et il RETIENT.

- **PUBLINDIE FAIT TOUT — DÉCIDÉ (Jordan, 19 octobre 2026 : « gonfler publindie pour qu'il fasse tout »)**, écrit par
  spannergames-71 :
  - `destinations.py` : les formats de chaque VITRINE (itch.io : 3 Mo par fichier, GIF compris ; Steam : captures
    1920 × 1080 en 16:9, au moins 5, les capsules ; le site : WebP 960 / 1920 / 2560, boucles de 6 Mo) — relevés le 19
    octobre 2026, sources dans le fichier ;
  - `vitrine PROJET DEST` : d'une liste (`06_boutique/<dest>/vitrine.json`) au lot prêt à téléverser — images (JPEG, ou
    WebP pour le site), GIF, boucles muettes WebM + MP4 + image d'attente — qui tient TOUT SEUL sous les poids de la
    vitrine (qualité, images par seconde, largeur, CRF, puis débit plafonné), et DIT ce qu'il a cédé ; vérifié ; la
    planche (`lot/planche.png`) à regarder avant de téléverser ;
  - `capturer RECETTE.json` : Godot photographie et filme une SCÈNE (un jeu, un monde posé par le greffon) dans un
    SubViewport à la taille EXACTE, films à pas fixe (`--fixed-fps`), HUD caché (`cacher_interface`) ;
  - `aligner` : l'ALIGNEMENT de `SpannerGames/CLAUDE.md` §0 (pousser, exporter ce dont le commit a bougé —
    `ATELIER/<P>/builds/DERNIER_EXPORT.txt` —, Publindie, le site et son aperçu), sur le PC ; `SpannerGames/OUTILS/
    rapatrier.sh` fait l'étape du téléphone.

## MESURÉ (19 octobre 2026)

- 22 tests sur le PC (`python -m unittest discover -s tests`, 343 s) ; la limite de poids des vitrines cassée exprès
  (`if False`) les fait rougir. Sur le téléphone, ffmpeg y est 3 à 4 fois plus lent (875 s) : les tests se lancent au PC.
- `capturer` sur WaterDrop (`SpannerGames/PROJETS/MarchingBlocks/01_scripts/recettes/waterdrop_godot.json`) : 4 images
  1920 × 1080 et un survol de 6 s à 30 images/s, du premier coup ; le HUD et les éléments de test du jeu cachés au
  second essai. Rendu par SSH : Godot trouve la RTX 2060 (Vulkan) même lancé hors du bureau.
- ⚠ Une mire au bruit total (`noise=allf=t`) est pire que n'importe quelle vraie image : un GIF de bruit ne tient pas
  3 Mo même réduit. `vitrine` le dit (« même réduit, le GIF dépasse ») au lieu de livrer — le comportement voulu.

## MESURÉ (18 octobre 2026)

- `python -m unittest discover -s tests` : 10 tests, sur un studio jetable ; cinq mutations rouges (le lien de X compté
  en entier, le lien en réponse ignoré, le journal non écrit, les orphelins qui ignorent les fiches, le poids ignoré).
- Les 4 fiches de MarchingBlocks (la station, le monde cartoon) : textes conformes à toutes les limites.

## OUVERT

- Verser ici `short_texte.py` (les Shorts à texte incrusté, aujourd'hui dans `PROJETS/MarchingBlocks/07_publication/
  outils/`) et ses recettes par projet.
- `capturer` ne filme pas l'APPLI MarchingBlocks (ses gestes passent par ses vrais outils : `DEV_TOOLS/filmer_*.gd`).
- Ranger les 121 exports de MarchingBlocks (13,7 Go) : `ranger` les liste, rien n'est déplacé (des scripts citent leurs
  chemins).
- Une interface (page web locale) par-dessus la ligne de commande, si l'usage le demande.
