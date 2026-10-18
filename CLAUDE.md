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

## MESURÉ (18 octobre 2026)

- `python -m unittest discover -s tests` : 10 tests, sur un studio jetable ; cinq mutations rouges (le lien de X compté
  en entier, le lien en réponse ignoré, le journal non écrit, les orphelins qui ignorent les fiches, le poids ignoré).
- Les 4 fiches de MarchingBlocks (la station, le monde cartoon) : textes conformes à toutes les limites.

## OUVERT

- Verser ici `short_texte.py` (les Shorts à texte incrusté, aujourd'hui dans `PROJETS/MarchingBlocks/07_publication/
  outils/`) et ses recettes par projet.
- Ranger les 121 exports de MarchingBlocks (13,7 Go) : `ranger` les liste, rien n'est déplacé (des scripts citent leurs
  chemins).
- Une interface (page web locale) par-dessus la ligne de commande, si l'usage le demande.
