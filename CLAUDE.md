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
  REVÉRIFIER sur les centres d'aide ; la plus petite valeur annoncée quand ils divergent. Bluesky et YouTube revérifiés
  sur leurs sources officielles le 21 octobre 2026 (voir « Poster sur Bluesky et YouTube »).
- ~~**PUBLINDIE NE PUBLIE PAS** : les plateformes n'ont pas d'API ouverte pour tout (itch, les annonces Steam) ou la font
  payer (X), et un humain publie. Il PRÉPARE et il RETIENT.~~ Remplacé le 21 octobre 2026 par la ligne qui suit.
- **PUBLINDIE POSTE LUI-MÊME SUR BLUESKY ET SUR YOUTUBE (vidéos et Shorts) — DÉCIDÉ (Jordan, 21 octobre 2026, à la
  question « Publindie peut poster des Shorts ? » : « Les deux »).** `python -m publindie poster PROJET ID` part d'une
  fiche, refuse si `verifier` y trouve une faute ou si le journal dit la publication déjà partie sur ce réseau, et écrit
  le journal dès que le post est en ligne. **Les autres réseaux restent MANUELS** (`preparer`, puis `marquer`) : l'API de
  X est payante ; TikTok et Instagram exigent une application validée par la plateforme ; itch.io et les annonces Steam
  n'ont pas d'API de publication ouverte.
- **AUCUN POST PAR ACCIDENT — PROPOSÉ (Claude, 21 octobre 2026)** : `poster` fait un ESSAI par défaut, TOUJOURS (il
  montre réseau, compte, fichiers, textes, facettes, visibilité, quota, sans ouvrir la moindre session) ; seul
  `--pour-de-vrai` envoie. Une session Claude ne lance `--pour-de-vrai` qu'avec l'accord de Jordan pour CETTE
  publication-là.
- **LES SECRETS NE SONT JAMAIS DANS UN DÉPÔT — DÉCIDÉ (Jordan, 21 octobre 2026)** : `C:/Users/jorda/.publindie/`
  (`chemins.SECRETS` : la variable `PUBLINDIE_SECRETS`, sinon la clé « secrets » du `publindie.json`, sinon
  `~/.publindie`). `.gitignore` rattrape un secret déposé ici par erreur. Claude ne crée aucun compte, n'entre aucun mot
  de passe et ne fait aucune connexion à la place de Jordan : la commande dit quoi créer et où le déposer, et s'arrête
  (code 2) si le secret manque.

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

## POSTER SUR BLUESKY ET YOUTUBE — le mode d'emploi (21 octobre 2026)

```
python -m publindie poster PROJET ID                       # ESSAI : ce qui partirait, sur chaque réseau automatique
python -m publindie poster PROJET ID --reseau youtube      # un seul réseau (bluesky | youtube | youtube_short)
python -m publindie poster PROJET ID --reseau bluesky --pour-de-vrai     # le post PART (accord de Jordan)
python -m publindie connecter bluesky [PROJET]             # Jordan, une fois : tester le compte (ne poste rien)
python -m publindie connecter youtube                      # Jordan, une fois : consentir dans son navigateur
```

Codes : 0 posté (ou essai prêt), 1 refusé (faute, déjà parti, échec dit), 2 secret manquant (le mode d'emploi s'affiche).
Ce que la fiche peut dire en plus : Bluesky — `alt` (OBLIGATOIRE pour une image ou un GIF : Publindie refuse sans),
`media` en liste pour 2 à 4 images (et `alt` en liste), `premiere_reponse` (part en réponse), `langs` (défaut `["en"]`) ;
YouTube — `visibilite` (public par défaut, unlisted, private), `publier_a` (date ISO : privée jusque-là), `miniature`
(une clé de `medias`, PNG ou JPEG), `playlist` (l'identifiant PL…), `notifier` (prévenir les abonnés, oui par défaut),
`categorie` (20, Gaming, par défaut), `contenu_synthetique` (la case « altered or synthetic content »), `pour_enfants`.

### Ce que Jordan fait UNE FOIS — OUVERT (rien de fait au 21 octobre 2026)

**Bluesky** (un compte par projet possible : `bluesky_<Projet>.json`, sinon `bluesky.json` sert à tous) :
1. bsky.app, connecté au compte qui postera : **Settings → Privacy and security → App passwords → Add App Password**,
   nommé « Publindie », SANS l'accès aux messages privés ; copier le mot de passe `xxxx-xxxx-xxxx-xxxx` (affiché une
   seule fois). Publindie REFUSE tout ce qui n'a pas cette forme : le mot de passe du compte ne se dépose jamais.
2. Vérifier l'adresse e-mail du compte (Settings → Account) : sans elle, Bluesky refuse les vidéos.
3. Écrire `C:/Users/jorda/.publindie/bluesky.json` :
   `{"identifiant": "<pseudo>.bsky.social", "mot_de_passe_application": "xxxx-xxxx-xxxx-xxxx"}`
4. `python -m publindie connecter bluesky` : dit le compte, le PDS, l'e-mail vérifié ou non, le quota vidéo du jour.

**YouTube** (console.cloud.google.com, avec le compte Google qui possède la chaîne SpannerGames) :
1. Créer un projet « Publindie ».
2. APIs & Services → Library → **YouTube Data API v3** → Enable.
3. **Google Auth Platform** (l'écran de consentement) : type **External**, nom « Publindie », e-mail de contact ;
   Audience : s'ajouter en utilisateur de test, puis **Publish app** (« In production »). ⚠ En mode « Testing », Google
   fait expirer le jeton de rafraîchissement en **7 jours** (developers.google.com/identity/protocols/oauth2) ; en
   production l'appli reste « non vérifiée » (un avertissement à passer une fois : Advanced → Go to Publindie), ce qui
   suffit pour son propre compte.
4. Clients → **Create client → Desktop app** → télécharger le JSON.
5. Le déposer sous `C:/Users/jorda/.publindie/youtube/client_secret.json`.
6. `python -m publindie connecter youtube` : le navigateur s'ouvre, choisir la chaîne **SpannerGames**, accepter ; le
   jeton s'écrit dans `.publindie/youtube/jeton.json` et se rafraîchit ensuite seul. (Six mois sans servir, il expire.)
7. Pour la miniature personnalisée : la chaîne doit être vérifiée par téléphone (youtube.com/verify).
8. L'**audit** (« YouTube API Services - Audit and Quota Extension Form ») : seulement si la première vidéo ressort
   privée (voir plus bas) ou si 100 envois par jour ne suffisent plus.

### Ce qui a été vérifié sur les sources officielles — MESURÉ (lu le 21 octobre 2026)

- **Bluesky** (docs.bsky.app, sources de `bluesky-social/bsky-docs` et lexiques de `bluesky-social/atproto`) : texte de
  **300 graphèmes et 3 000 octets** ; facettes en **octets UTF-8**, fin exclue (lien `#link`, hashtag `#tag` sans le
  « # ») ; **4 images** de **2 000 000 octets** au plus (le guide des posts dit encore 1 000 000 : le lexique fait foi),
  `alt` requis par le lexique ; vidéo **MP4 seulement, 300 000 000 octets**, adresse e-mail vérifiée, quota par jour
  (`app.bsky.video.getUploadLimits`). La voie vidéo RECOMMANDÉE (tutoriel « Uploading Video ») : `getServiceAuth`
  (audience `did:web:<hôte du PDS>`, méthode `com.atproto.repo.uploadBlob`, 30 minutes) → `video.bsky.app/xrpc/
  app.bsky.video.uploadVideo?did=…&name=…` → `getJobStatus` jusqu'au blob ; `uploadBlob` direct marche aussi mais le
  post paraît avant la fin du traitement. Un GIF part en MP4 muet avec `presentation: "gif"`. ⚠ Le lexique a gagné une
  voie en morceaux (`startUpload` / `uploadPart` / `finishUpload`) : pas utilisée, la voie du tutoriel suffit à 300 Mo.
- **YouTube** (developers.google.com) : `videos.insert` (page mise à jour le 15 octobre 2026), envoi reprenable, portée
  `youtube.upload` (+ `youtube` pour la playlist). ⚠ **DEUX PRÉMISSES PÉRIMÉES** : (1) le QUOTA — depuis juin 2026
  `videos.insert` a son propre seau « Video Uploads » : **100 envois par jour, 1 unité chacun** (≈ 1 600 unités jusqu'en
  décembre 2025, puis ≈ 100) ; `thumbnails.set` ≈ 50 unités et `playlistItems.insert` 50 sur les 10 000 du seau commun ;
  (2) le VERROU PRIVÉ — la règle du 28 juillet 2020 (projets non audités → vidéos privées) reste dans l'historique des
  révisions, mais la référence dit aujourd'hui : « Videos uploaded from unverified API projects are not restricted to
  private viewing mode. » Des guides de tiers de 2026 disent encore l'inverse. **OUVERT jusqu'au premier envoi** :
  `poster` compare la visibilité que YouTube rend à celle demandée, le dit en clair et l'écrit au journal
  (`visibilite`). **Short** : 3 minutes au plus, carré ou vertical, #Shorts facultatif (support.google.com/youtube/
  answer/15424877) — `reseaux.py` accepte désormais le carré.
- `reseaux.py` compte Bluesky en GRAPHÈMES (« 👨‍❤️‍👨 » vaut 1 ; module `regex`, approximation sans lui) et en octets ;
  il vérifie les 500 caractères de tags YouTube et les `<` `>` interdits dans un titre.

### MESURÉ (21 octobre 2026)

- 17 tests neufs (`tests/test_poster.py`), 39 en tout, verts (427 s) : un FAUX serveur Bluesky (http.server sur
  127.0.0.1) reçoit les vrais appels HTTP (session, blob, service vidéo et son attente, post, réponse) ; un FAUX service
  YouTube reçoit le corps, la miniature, la playlist, et rend « private » pour éprouver l'avertissement. Aucun appel
  réseau réel, aucun compte.
- **Deux mutations rouges** : le journal ignoré (3 tests rougissent : la publication repart sur Bluesky comme sur
  YouTube) ; `verifier` ignoré (un texte de 301 caractères est réellement reçu par le faux serveur, code 0 au lieu de 1).
- L'essai sur la vraie fiche `MarchingBlocks/monde_cartoon` : Bluesky REFUSÉ (le GIF n'a pas de texte alternatif) ;
  YouTube prêt (352 Mo, 1920 × 1080), OAuth absent. Rien d'écrit dans `07_publication`. `verifier` rend le même verdict
  qu'avant sur les fiches de MarchingBlocks.
- ⚠ Installer `google-api-python-client` (2.201.0) et `google-auth-oauthlib` (1.5.0) montait protobuf en 7.x, hors de
  ce que wandb accepte (< 7) : ramené à 6.33.5, qui va à Google, wandb, tensorboard et aider. `descript-audiotools`
  (exige < 3.20) était déjà incompatible avec wandb avant.
- **PAS ENCORE FAIT : aucun post réel.** Le premier se fera avec l'accord de Jordan pour CETTE publication.

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
