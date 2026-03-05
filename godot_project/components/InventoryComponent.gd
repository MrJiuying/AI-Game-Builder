extends Node
class_name InventoryComponent

signal item_changed(item_id: String, current_count: int)
signal inventory_changed()

@export var max_slots: int = 24
@export var stack_limit: int = 99
@export var allow_new_items: bool = true

var _items: Dictionary = {}

func add_item(item_id: String, count: int = 1) -> int:
	var safe_id: String = item_id.strip_edges()
	var safe_count: int = max(count, 0)
	if safe_id == "" or safe_count <= 0:
		return 0
	if not _items.has(safe_id):
		if not allow_new_items:
			return 0
		if _items.size() >= max(max_slots, 0):
			return 0
		_items[safe_id] = 0

	var prev: int = int(_items[safe_id])
	var next: int = min(prev + safe_count, max(stack_limit, 1))
	_items[safe_id] = next
	var added: int = next - prev
	if added > 0:
		item_changed.emit(safe_id, next)
		inventory_changed.emit()
	return added

func remove_item(item_id: String, count: int = 1) -> int:
	var safe_id: String = item_id.strip_edges()
	var safe_count: int = max(count, 0)
	if safe_id == "" or safe_count <= 0:
		return 0
	if not _items.has(safe_id):
		return 0

	var prev: int = int(_items[safe_id])
	var next: int = max(prev - safe_count, 0)
	var removed: int = prev - next
	if next == 0:
		_items.erase(safe_id)
	else:
		_items[safe_id] = next

	if removed > 0:
		item_changed.emit(safe_id, next)
		inventory_changed.emit()
	return removed

func set_item_count(item_id: String, count: int) -> void:
	var safe_id: String = item_id.strip_edges()
	if safe_id == "":
		return
	var safe_count: int = max(count, 0)
	if safe_count == 0:
		if _items.has(safe_id):
			_items.erase(safe_id)
			item_changed.emit(safe_id, 0)
			inventory_changed.emit()
		return

	if not _items.has(safe_id):
		if _items.size() >= max(max_slots, 0):
			return
	_items[safe_id] = min(safe_count, max(stack_limit, 1))
	item_changed.emit(safe_id, int(_items[safe_id]))
	inventory_changed.emit()

func get_item_count(item_id: String) -> int:
	var safe_id: String = item_id.strip_edges()
	if safe_id == "" or not _items.has(safe_id):
		return 0
	return int(_items[safe_id])

func has_item(item_id: String, count: int = 1) -> bool:
	return get_item_count(item_id) >= max(count, 1)

func clear_inventory() -> void:
	if _items.is_empty():
		return
	_items.clear()
	inventory_changed.emit()

func get_all_items() -> Dictionary:
	return _items.duplicate(true)
