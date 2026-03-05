extends Node
class_name ProjectileShooterComponent

@export var projectile_scene: PackedScene
@export var muzzle_path: NodePath
@export var fire_action: StringName = &"ui_accept"
@export var fire_rate: float = 0.25
@export var projectile_speed: float = 500.0
@export var projectile_lifetime: float = 2.0
@export var damage: float = 10.0
@export var auto_fire: bool = false
@export var auto_fire_group: StringName = &"enemy"
@export var shoot_enabled: bool = true

var _owner_node: Node2D
var _cooldown: float = 0.0

func _ready() -> void:
	_owner_node = get_parent() as Node2D
	if _owner_node == null:
		set_process(false)

func _process(delta: float) -> void:
	if _owner_node == null or not is_instance_valid(_owner_node):
		return
	if not shoot_enabled:
		return

	_cooldown = max(_cooldown - delta, 0.0)
	if _cooldown > 0.0:
		return

	var should_fire := auto_fire or Input.is_action_pressed(fire_action)
	if not should_fire:
		return

	var dir := _get_fire_direction()
	if dir == Vector2.ZERO:
		return

	_spawn_projectile(dir.normalized())
	_cooldown = max(fire_rate, 0.01)

func _get_fire_direction() -> Vector2:
	if auto_fire:
		var target := _find_nearest_target()
		if target == null:
			return Vector2.ZERO
		return target.global_position - _get_muzzle_position()

	if _owner_node.get_viewport() == null:
		return Vector2.ZERO
	var mouse_pos := _owner_node.get_global_mouse_position()
	return mouse_pos - _get_muzzle_position()

func _find_nearest_target() -> Node2D:
	if get_tree() == null:
		return null
	var origin := _get_muzzle_position()
	var nearest: Node2D
	var best_dist := INF
	for node in get_tree().get_nodes_in_group(auto_fire_group):
		if node is Node2D and node != _owner_node:
			var d := origin.distance_to((node as Node2D).global_position)
			if d < best_dist:
				best_dist = d
				nearest = node as Node2D
	return nearest

func _get_muzzle_position() -> Vector2:
	if not muzzle_path.is_empty():
		var n := get_node_or_null(muzzle_path)
		if n is Node2D:
			return (n as Node2D).global_position
	return _owner_node.global_position

func _spawn_projectile(direction: Vector2) -> void:
	var projectile: Node2D
	if projectile_scene != null:
		var instance := projectile_scene.instantiate()
		if instance is Node2D:
			projectile = instance as Node2D
	if projectile == null:
		projectile = Area2D.new()

	projectile.global_position = _get_muzzle_position()
	if projectile.has_method("configure_projectile"):
		projectile.call("configure_projectile", direction, projectile_speed, damage, projectile_lifetime)
	else:
		if "velocity" in projectile:
			projectile.set("velocity", direction * projectile_speed)
		if "direction" in projectile:
			projectile.set("direction", direction)
		if "speed" in projectile:
			projectile.set("speed", projectile_speed)
		if "damage" in projectile:
			projectile.set("damage", damage)

	var scene := get_tree().current_scene if get_tree() != null else null
	if scene != null:
		scene.add_child(projectile)
	else:
		add_child(projectile)

	if projectile_lifetime > 0.0:
		_destroy_later(projectile, projectile_lifetime)

func _destroy_later(node: Node, t: float) -> void:
	await get_tree().create_timer(t).timeout
	if node != null and is_instance_valid(node):
		node.queue_free()
