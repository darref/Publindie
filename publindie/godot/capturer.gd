# LE PHOTOGRAPHE DE PUBLINDIE — une scène Godot, une recette de plans, des images à la taille EXACTE.
#
#   godot --path PROJET --script <ce fichier> [--fixed-fps 30] -- --recette=R.json --sortie=DOSSIER [--seulement=NOM]
#
# Lancé par `python -m publindie capturer` (qui prépare la recette résolue) : ne pas l'appeler à la main.
# ⚠ LA SCÈNE EST RENDUE DANS UN SubViewport de la taille voulue, pas dans la fenêtre : la fenêtre de Godot sort parfois
#   plus petite que `--resolution` (leçon de River Stones et de MarchingBlocks), un SubViewport jamais.
# ⚠ UN FILM EST UNE SUITE DE PNG À PAS FIXE (`--fixed-fps`) : l'eau animée par TIME avance d'un pas exact par image,
#   même si la machine rame (la règle de `--write-movie`, sans ses tailles de fenêtre).
# ⚠ LA SCÈNE N'EST JAMAIS ENREGISTRÉE : on la charge, on la photographie, on quitte.
extends SceneTree

var recette := {}
var sortie := ""
var seulement := ""
var vue: SubViewport
var camera: Camera3D
var scene: Node


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--recette="):
			recette = JSON.parse_string(FileAccess.get_file_as_string(a.substr(10)))
		elif a.begins_with("--sortie="):
			sortie = a.substr(9)
		elif a.begins_with("--seulement="):
			seulement = a.substr(12)
	if recette == null or recette.is_empty() or sortie == "":
		printerr("PUBLINDIE : recette ou sortie manquante")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(sortie)
	var taille: Array = recette.get("taille", [1920, 1080])
	vue = SubViewport.new()
	vue.size = Vector2i(int(taille[0]), int(taille[1]))
	vue.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vue.msaa_3d = Viewport.MSAA_4X
	vue.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	root.add_child(vue)
	var paquet: PackedScene = load(recette["scene"])
	if paquet == null:
		printerr("PUBLINDIE : scène illisible : ", recette["scene"])
		quit(3)
		return
	scene = paquet.instantiate()
	vue.add_child(scene)
	camera = Camera3D.new()
	camera.far = float(recette.get("loin", 4000.0))
	vue.add_child(camera)
	_tourner.call_deferred()


func _noeud(chemin: String) -> Node:
	var n := scene.get_node_or_null(chemin)
	if n == null:
		n = scene.find_child(chemin, true, false)
	if n == null:
		print("PUBLINDIE ⚠ nœud introuvable : ", chemin)
	return n


## Le HUD d'un jeu (textes d'aide, états de test) n'a rien à faire dans une capture de vitrine : chaque CanvasLayer et
## chaque Control de premier niveau est caché. ⚠ Un effet posé en CanvasLayer (un cercle d'occlusion…) l'est aussi.
func _cacher_interface(n: Node) -> void:
	for e in n.get_children():
		if e is CanvasLayer:
			e.visible = false
		elif e is Control and not (e.get_parent() is CanvasItem):
			e.visible = false
		else:
			_cacher_interface(e)


func _attendre(images: int) -> void:
	for i in images:
		await process_frame


func _poser(oeil: Array, cible: Array, fov: float) -> void:
	camera.fov = fov
	camera.global_position = Vector3(oeil[0], oeil[1], oeil[2])
	var c := Vector3(cible[0], cible[1], cible[2])
	var haut := Vector3.UP if abs((c - camera.global_position).normalized().y) < 0.99 else Vector3.FORWARD
	camera.look_at(c, haut)
	camera.make_current()


func _soleil(s: Dictionary) -> void:
	var n := _noeud(s.get("noeud", "Sun"))
	if n is DirectionalLight3D:
		# l'azimut se compte depuis le nord (−Z) vers l'est (+X) ; la lumière éclaire le long de son −Z.
		n.rotation_degrees = Vector3(-float(s.get("elevation", 35)), -float(s.get("azimut", 200)), 0)
		if s.has("energie"):
			n.light_energy = float(s["energie"])
		if s.has("couleur"):
			n.light_color = Color(s["couleur"])


func _photo(nom: String) -> void:
	await RenderingServer.frame_post_draw
	var chemin := sortie.path_join(nom + ".png")
	vue.get_texture().get_image().save_png(chemin)
	print("PUBLINDIE image ", chemin)


func _tourner() -> void:
	await _attendre(int(recette.get("attente_depart", 120)))
	for chemin in recette.get("cacher", []):
		var n := _noeud(chemin)
		if n is Node3D or n is CanvasItem or n is CanvasLayer:
			n.visible = false
	if recette.get("cacher_interface", false):
		_cacher_interface(scene)
	for chemin in recette.get("figer", []):
		var n := _noeud(chemin)
		if n:
			n.process_mode = Node.PROCESS_MODE_DISABLED
	if recette.has("soleil"):
		_soleil(recette["soleil"])
	for p in recette.get("plans", []):
		if seulement != "" and p["nom"] != seulement:
			continue
		if p.has("soleil"):
			_soleil(p["soleil"])
		var fov := float(p.get("fov", recette.get("fov", 50.0)))
		if not p.has("film"):
			_poser(p["oeil"], p["cible"], fov)
			await _attendre(int(p.get("attente", recette.get("attente", 20))))
			await _photo(p["nom"])
			continue
		var f: Dictionary = p["film"]
		var n := int(round(float(f.get("secondes", 6.0)) * float(f.get("fps", 30))))
		var dossier := sortie.path_join(p["nom"])
		DirAccess.make_dir_recursive_absolute(dossier)
		_poser(p["oeil"], p["cible"], fov)
		await _attendre(int(p.get("attente", recette.get("attente", 20))))
		for i in n:
			var t := float(i) / float(max(n - 1, 1))
			t = t * t * (3.0 - 2.0 * t)                    # départ et arrivée en douceur
			var o: Array = p["oeil"]; var o2: Array = f.get("fin_oeil", o)
			var c: Array = p["cible"]; var c2: Array = f.get("fin_cible", c)
			_poser([lerpf(o[0], o2[0], t), lerpf(o[1], o2[1], t), lerpf(o[2], o2[2], t)],
				[lerpf(c[0], c2[0], t), lerpf(c[1], c2[1], t), lerpf(c[2], c2[2], t)],
				lerpf(fov, float(f.get("fin_fov", fov)), t))
			await RenderingServer.frame_post_draw
			vue.get_texture().get_image().save_png(dossier.path_join("%05d.png" % i))
			await process_frame
		print("PUBLINDIE film ", dossier, " ", n)
	print("PUBLINDIE fini")
	quit(0)
