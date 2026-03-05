extends Area2D
class_name CollectibleComponent

signal collected(collector: Node, item_id: String, amount: int)

@export var item_id: String = "coin"
@export var amount: int = 1
@export var collector_group: StringName = &"player"
@export var auto_collect: bool = true
@export var pickup_action: StringName = &"ui_accept"
@export var destroy_on_collect: bool = true
@export var enabled: bool = true

var _near_collectors: Array[Node] = []

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _process(_delta: float) -> void:
	if not enabled or auto_collect:
		return
	if not Input.is_action_just_pressed(pickup_action):
		return
	var collector := _get_first_valid_collector()
	if collector == null:
		return
	_collect(collector)

func _on_body_entered(body: Node) -> void:
	if not enabled:
		return
	if not _can_collect(body):
		return
	if not _near_collectors.has(body):
		_near_collectors.append(body)
	if auto_collect:
		_collect(body)

func _on_body_exited(body: Node) -> void:
	_near_collectors.erase(body)

func _can_collect(body: Node) -> bool:
	if body == null or not is_instance_valid(body):
		return false
	if collector_group == StringName():
		return true
	return body.is_in_group(collector_group)

func _get_first_valid_collector() -> Node:
	for node in _near_collectors:
		if node != null and is_instance_valid(node) and _can_collect(node):
			return node
	return null

func _collect(collector: Node) -> void:
	if collector == null or not is_instance_valid(collector):
		return
	var safe_id := item_id.strip_edges()
	if safe_id == "":
		safe_id = "item"
	var safe_amount := max(amount, 1)

	var inventory := collector.get_node_or_null("InventoryComponent")
	if inventory != null and inventory.has_method("add_item"):
		inventory.call("add_item", safe_id, safe_amount)
	elif collector.has_method("add_item"):
		collector.call("add_item", safe_id, safe_amount)

	collected.emit(collector, safe_id, safe_amount)
	if destroy_on_collect:
		queue_free()
