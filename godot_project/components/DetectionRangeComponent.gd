extends Node
class_name DetectionRangeComponent

signal target_entered(target: Node2D)
signal target_exited(target: Node2D)

@export var detection_radius: float = 220.0
@export var target_group: StringName = &"player"
@export var update_interval: float = 0.1
@export var detect_enabled: bool = true

var _host: Node2D
var _elapsed: float = 0.0
var _detected_map: Dictionary = {}
var current_target: Node2D

func _ready() -> void:
	_host = get_parent() as Node2D
	if _host == null:
		set_physics_process(false)

func _physics_process(delta: float) -> void:
	if _host == null or not is_instance_valid(_host):
		return
	if not detect_enabled:
		_detected_map.clear()
		current_target = null
		return

	_elapsed += delta
	if _elapsed < max(update_interval, 0.01):
		return
	_elapsed = 0.0
	_scan_targets()

func _scan_targets() -> void:
	if get_tree() == null:
		return
	var next_map: Dictionary = {}
	var nearest: Node2D
	var best_dist := INF
	for node in get_tree().get_nodes_in_group(target_group):
		if not (node is Node2D):
			continue
		var target := node as Node2D
		if target == _host:
			continue
		var d := _host.global_position.distance_to(target.global_position)
		if d > max(detection_radius, 0.0):
			continue
		next_map[target.get_instance_id()] = target
		if d < best_dist:
			best_dist = d
			nearest = target

	for id in next_map.keys():
		if not _detected_map.has(id):
			target_entered.emit(next_map[id] as Node2D)
	for id in _detected_map.keys():
		if not next_map.has(id):
			var old_target = _detected_map[id]
			if old_target is Node2D and is_instance_valid(old_target):
				target_exited.emit(old_target as Node2D)

	_detected_map = next_map
	current_target = nearest

func get_detected_targets() -> Array[Node2D]:
	var list: Array[Node2D] = []
	for value in _detected_map.values():
		if value is Node2D and is_instance_valid(value):
			list.append(value as Node2D)
	return list
