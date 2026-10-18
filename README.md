# Publindie

**Les outils de publication d'un studio indé** : fabriquer les médias depuis le vrai produit (vidéo, Short, GIF,
miniature, voix), les ranger, préparer chaque post pour chaque réseau, et tenir le journal de ce qui est parti où.

Né le 18 octobre 2026 des outils de SpannerGames (`SpannerGames/OUTILS`), à la demande de Jordan : « améliore les outils
de publication et le rangement de ses sources et de ses exports, comme un projet à part ». Le code vit ici ; les médias
vivent dans le dossier du studio, décrit par son `publindie.json`.

```
python -m publindie chemins                      # le studio, ses outils, ses projets
python -m publindie projet NOM                   # l'arbre d'un projet (01_scripts … 07_publication)
python -m publindie ranger [NOM]                 # ce qui est où, ce qui traîne, les exports sans fiche
python -m publindie verifier [NOM]               # chaque fiche contre les limites de chaque réseau
python -m publindie preparer NOM [ID]            # la feuille de route : quoi joindre, quoi coller, où
python -m publindie marquer NOM ID RESEAU [URL]  # « c'est parti »
python -m publindie calendrier [--jours 14]      # ce qui est prévu, jour par jour, tous projets
python -m publindie reseaux                      # les limites relevées
python -m publindie.video couper|monter|musique|short|planche|gif|verifier …
python -m publindie.miniature · .voix · .capture · .chaine
```

Le studio : la variable `PUBLINDIE_STUDIO`, sinon `D:/SpannerGames`. Tests : `python -m unittest discover -s tests`.
