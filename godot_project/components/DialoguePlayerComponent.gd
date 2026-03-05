extends Node
class_name DialoguePlayerComponent

signal dialogue_started()
signal dialogue_finished()
signal line_changed(line_index: int, line_text: String)

@export var dialogue_lines: PackedStringArray = []
@export var typing_speed: float = 0.03
@export var advance_action: StringName = &"ui_accept"
@export var panel_size: Vector2 = Vector2(860, 200)
@export var panel_margin_bottom: float = 28.0
@export var auto_hide_on_finish: bool = true
@export var enabled: bool = true

var _canvas_layer: CanvasLayer
var _panel: PanelContainer
var _label: RichTextLabel
var _typing_timer: Timer
var _line_index: int = -1
var _char_index: int = 0
var _is_playing: bool = false
var _current_line: String = ""

func _ready() -> void:
	_ensure_ui()

func start_dialogue(lines: PackedStringArray = PackedStringArray()) -> void:
	if not enabled:
		return
	_ensure_ui()
	if lines.size() > 0:
		dialogue_lines = lines
	if dialogue_lines.is_empty():
		_stop_dialogue(false)
		return
	_is_playing = true
	_line_index = -1
	_panel.visible = true
	dialogue_started.emit()
	_show_next_line()

func advance_dialogue() -> void:
	if not _is_playing:
		return
	if _char_index < _current_line.length():
		_char_index = _current_line.length()
		_label.text = _current_line
		_typing_timer.stop()
		return
	_show_next_line()

func stop_dialogue() -> void:
	_stop_dialogue(true)

func _unhandled_input(event: InputEvent) -> void:
	if not enabled or not _is_playing:
		return
	if event.is_action_pressed(advance_action):
		advance_dialogue()
		get_viewport().set_input_as_handled()

func _ensure_ui() -> void:
	if _canvas_layer != null and is_instance_valid(_canvas_layer):
		return
	_canvas_layer = CanvasLayer.new()
	_canvas_layer.name = "DialogueCanvasLayer"
	add_child(_canvas_layer)

	_panel = PanelContainer.new()
	_panel.name = "DialoguePanel"
	_panel.visible = false
	_panel.custom_minimum_size = panel_size
	_panel.anchor_left = 0.5
	_panel.anchor_right = 0.5
	_panel.anchor_top = 1.0
	_panel.anchor_bottom = 1.0
	_panel.offset_left = -panel_size.x * 0.5
	_panel.offset_right = panel_size.x * 0.5
	_panel.offset_top = -panel_size.y - panel_margin_bottom
	_panel.offset_bottom = -panel_margin_bottom
	_canvas_layer.add_child(_panel)

	_label = RichTextLabel.new()
	_label.name = "DialogueLabel"
	_label.fit_content = true
	_label.scroll_active = false
	_label.bbcode_enabled = false
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel.add_child(_label)

	_typing_timer = Timer.new()
	_typing_timer.name = "TypingTimer"
	_typing_timer.one_shot = false
	_typing_timer.wait_time = max(typing_speed, 0.005)
	_typing_timer.timeout.connect(_on_typing_tick)
	add_child(_typing_timer)

func _show_next_line() -> void:
	_line_index += 1
	if _line_index >= dialogue_lines.size():
		_stop_dialogue(true)
		return
	_current_line = dialogue_lines[_line_index]
	_char_index = 0
	_label.text = ""
	_typing_timer.wait_time = max(typing_speed, 0.005)
	_typing_timer.start()
	line_changed.emit(_line_index, _current_line)

func _on_typing_tick() -> void:
	if not _is_playing:
		_typing_timer.stop()
		return
	if _char_index >= _current_line.length():
		_typing_timer.stop()
		return
	_char_index += 1
	_label.text = _current_line.substr(0, _char_index)

func _stop_dialogue(emit_finished: bool) -> void:
	_is_playing = false
	if _typing_timer != null and is_instance_valid(_typing_timer):
		_typing_timer.stop()
	if _panel != null and is_instance_valid(_panel):
		_panel.visible = not auto_hide_on_finish
	if emit_finished:
		dialogue_finished.emit()
