extends Node
class_name GameStateFlagComponent

signal flag_changed(flag_key: String, value: Variant)

static var _global_flags: Dictionary = {}

@export var namespace: String = "global"
@export var use_global_store: bool = true

var _local_flags: Dictionary = {}

func set_flag(flag_name: String, value: Variant) -> void:
	var key := _build_key(flag_name)
	if key == "":
		return
	if use_global_store:
		_global_flags[key] = value
	else:
		_local_flags[key] = value
	flag_changed.emit(key, value)

func get_flag(flag_name: String, default_value: Variant = null) -> Variant:
	var key := _build_key(flag_name)
	if key == "":
		return default_value
	if use_global_store:
		return _global_flags.get(key, default_value)
	return _local_flags.get(key, default_value)

func has_flag(flag_name: String) -> bool:
	var key := _build_key(flag_name)
	if key == "":
		return false
	if use_global_store:
		return _global_flags.has(key)
	return _local_flags.has(key)

func remove_flag(flag_name: String) -> void:
	var key := _build_key(flag_name)
	if key == "":
		return
	if use_global_store:
		if _global_flags.has(key):
			_global_flags.erase(key)
			flag_changed.emit(key, null)
	else:
		if _local_flags.has(key):
			_local_flags.erase(key)
			flag_changed.emit(key, null)

func toggle_flag(flag_name: String) -> bool:
	var current := bool(get_flag(flag_name, false))
	var next := not current
	set_flag(flag_name, next)
	return next

func increment_flag(flag_name: String, step: float = 1.0) -> float:
	var current := float(get_flag(flag_name, 0.0))
	var next := current + step
	set_flag(flag_name, next)
	return next

func get_snapshot() -> Dictionary:
	if use_global_store:
		return _global_flags.duplicate(true)
	return _local_flags.duplicate(true)

func _build_key(flag_name: String) -> String:
	var n := namespace.strip_edges()
	var f := flag_name.strip_edges()
	if f == "":
		return ""
	if n == "":
		return f
	return "%s.%s" % [n, f]
