class_name LiveLink
extends Node

## WebSocket 实时连接客户端 - 用于接收 AI 生成的实体配置广播
##
## 使用方法：
## 1. 在 Godot 中创建一个新场景
## 2. 添加一个 Node2D 根节点
## 3. 将此脚本挂载到根节点
## 4. 运行后会自动连接到 ws://localhost:8000/ws

const WS_URL: String = "ws://localhost:8000/ws"
const ASSEMBLER_PATH: String = "res://scripts/autoload/EntityAssembler.gd"

const RECONNECT_DELAY: float = 2.0
const HEARTBEAT_INTERVAL: float = 5.0

var _ws: WebSocketPeer = WebSocketPeer.new()
var _assembler: Node = null
var _current_entity: Node2D = null
var _is_connected: bool = false
var _heartbeat_timer: float = 0.0
var _reconnect_timer: float = 0.0


func _ready() -> void:
	_connect_to_server()
	_load_assembler()


func _connect_to_server() -> void:
	print("[LiveLink] 正在连接 WebSocket 服务器: %s" % WS_URL)
	
	var error = _ws.connect_to_url(WS_URL)
	if error != OK:
		push_error("[LiveLink] 无法连接到 WebSocket 服务器，错误码: %d" % error)
		_schedule_reconnect()
		return


func _load_assembler() -> void:
	if ResourceLoader.exists(ASSEMBLER_PATH):
		var assembler_script: GDScript = load(ASSEMBLER_PATH)
		if assembler_script != null:
			_assembler = assembler_script.new()
			print("[LiveLink] EntityAssembler 加载成功")
			return
	
	print("[LiveLink] EntityAssembler 不存在，使用内置版本")
	_assembler = _create_fallback_assembler()


func _process(delta: float) -> void:
	_ws.poll()
	
	var state = _ws.get_ready_state()
	
	match state:
		WebSocketPeer.STATE_OPEN:
			if not _is_connected:
				_is_connected = true
				print("[LiveLink] WebSocket 连接已建立!")
			
			_poll_messages()
			_send_heartbeat(delta)
			
		WebSocketPeer.STATE_CLOSED:
			if _is_connected:
				_is_connected = false
				var code = _ws.get_close_code()
				var reason = _ws.get_close_reason()
				print("[LiveLink] WebSocket 连接已关闭: 代码=%d, 原因=%s" % [code, reason])
			
			_schedule_reconnect(delta)
			
		WebSocketPeer.STATE_CONNECTING:
			pass
			
		WebSocketPeer.STATE_INVALID:
			_is_connected = false
			print("[LiveLink] WebSocket 连接无效，尝试重连...")
			_schedule_reconnect(delta)


func _poll_messages() -> void:
	while _ws.get_available_packet_count() > 0:
		var packet = _ws.get_packet()
		var message = packet.get_string_from_utf8()
		
		_handle_message(message)


func _handle_message(message: String) -> void:
	var json = JSON.new()
	var parse_result = json.parse(message)
	
	if parse_result != OK:
		push_warning("[LiveLink] JSON 解析失败: %s" % message)
		return
	
	var data = json.get_data()
	
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("[LiveLink] 收到的数据不是字典: %s" % str(data))
		return
	
	var action = data.get("action", "")
	
	match action:
		"spawn_entity":
			var config_path = data.get("config_path", "")
			if config_path != "":
				_spawn_entity(config_path)
			else:
				push_warning("[LiveLink] spawn_entity 缺少 config_path")
		
		"pong":
			print("[LiveLink] 收到心跳响应")
		
		_:
			print("[LiveLink] 收到未知 action: %s" % action)


func _send_heartbeat(delta: float) -> void:
	_heartbeat_timer += delta
	
	if _heartbeat_timer >= HEARTBEAT_INTERVAL:
		_heartbeat_timer = 0.0
		
		if _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
			var ping_msg = JSON.stringify({"action": "ping", "client": "godot"})
			var error = _ws.send_text(ping_msg)
			if error != OK:
				push_warning("[LiveLink] 发送心跳失败，错误码: %d" % error)
			else:
				print("[LiveLink] 发送心跳 ping")


func _schedule_reconnect(delta: float = 0.0) -> void:
	_reconnect_timer += delta
	
	if _reconnect_timer >= RECONNECT_DELAY:
		_reconnect_timer = 0.0
		print("[LiveLink] 尝试重新连接...")
		_connect_to_server()


func _spawn_entity(config_path: String) -> void:
	print("[LiveLink] 收到生成实体请求: %s" % config_path)
	
	if _current_entity != null:
		_current_entity.queue_free()
		_current_entity = null
	
	var new_entity: Node2D = null
	
	if _assembler != null and _assembler.has_method("build_entity_from_json"):
		new_entity = _assembler.build_entity_from_json(config_path)
	
	if new_entity == null:
		push_error("[LiveLink] 实体装配失败: %s" % config_path)
		return
	
	new_entity.position = Vector2(500, 300)
	add_child(new_entity)
	_current_entity = new_entity
	
	print("[LiveLink] 实体已生成并添加到场景: %s" % new_entity.name)


func _create_fallback_assembler() -> Node:
	var fallback: Node = Node.new()
	fallback.name = "FallbackAssembler"
	
	var assembler_script: GDScript = GDScript.new()
	assembler_script.source_code = """
extends Node

const COMPONENTS_PATH: String = "res://components/"

func build_entity_from_json(json_path: String) -> Node2D:
	var file = FileAccess.open(json_path, FileAccess.READ)
	if file == null:
		push_error("无法打开文件: " + json_path)
		return null
	
	var json_string = file.get_as_text()
	file.close()
	
	var json = JSON.new()
	var result = json.parse(json_string)
	if result != OK:
		push_error("JSON 解析失败")
		return null
	
	var data = json.get_data()
	return _build_from_dict(data)

func _build_from_dict(data: Dictionary) -> Node2D:
	var entity_name = data.get("entity_name", "Unnamed")
	var base_type = data.get("base_type", "Node2D")
	
	var entity: Node2D
	match base_type:
		"CharacterBody2D": entity = CharacterBody2D.new()
		"Area2D": entity = Area2D.new()
		"StaticBody2D": entity = StaticBody2D.new()
		_: entity = Node2D.new()
	
	entity.name = entity_name
	
	var components = data.get("components", [])
	var params = data.get("component_params", {})
	
	for comp_name in components:
		var script_path = COMPONENTS_PATH + comp_name + ".gd"
		if ResourceLoader.exists(script_path):
			var script = load(script_path)
			var comp = script.new()
			comp.name = comp_name
			entity.add_child(comp)
			
			var comp_params = params.get(comp_name, {})
			for prop in comp_params:
				comp.set(prop, comp_params[prop])
	
	var sprite_path = data.get("sprite_path")
	if sprite_path != null and ResourceLoader.exists(sprite_path):
		var sprite = Sprite2D.new()
		sprite.name = "Sprite"
		sprite.texture = load(sprite_path)
		if sprite.texture.get_size() != Vector2.ZERO:
			sprite.position = sprite.texture.get_size() / 2.0
		entity.add_child(sprite)
	
	return entity
"""
	assembler_script.reload()
	fallback.set_script(assembler_script)
	add_child(fallback)
	
	return fallback


func _exit_tree() -> void:
	if _ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		_ws.close()
		print("[LiveLink] WebSocket 连接已关闭")
