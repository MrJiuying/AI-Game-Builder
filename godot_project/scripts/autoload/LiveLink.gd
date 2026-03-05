extends Node

var websocket: WebSocketPeer
var server_url = "ws://localhost:8000/ws"
var current_entity: Node2D = null

func _ready():
	print("LiveLink: 正在连接 WebSocket...")
	connect_to_server()

func connect_to_server():
	websocket = WebSocketPeer.new()
	var err = websocket.connect_to_url(server_url)
	if err != OK:
		print("LiveLink: 连接失败，1秒后重试...")
		get_tree().create_timer(1.0).timeout.connect(connect_to_server)
	else:
		print("LiveLink: 已连接到 ", server_url)

func _process(delta):
	if websocket:
		websocket.poll()
		var state = websocket.get_ready_state()
		if state == WebSocketPeer.STATE_OPEN:
			while websocket.get_available_packet_count():
				var packet = websocket.get_packet()
				var data = packet.get_string_from_utf8()
				handle_message(data)
		elif state == WebSocketPeer.STATE_CLOSED:
			print("LiveLink: 连接已关闭，1秒后重试...")
			get_tree().create_timer(1.0).timeout.connect(connect_to_server)

func handle_message(message: String):
	print("LiveLink: 收到消息: ", message)
	var json = JSON.new()
	var parse_result = json.parse(message)
	if parse_result != OK:
		return
	
	var data = json.get_data()
	if data is Dictionary:
		var action = data.get("action", "")
		if action == "spawn_entity":
			spawn_entity(data)

func spawn_entity(data: Dictionary):
	var config_path = data.get("config_path", "")
	if config_path.is_empty():
		return
	
	# 清除之前的实体
	if current_entity and is_instance_valid(current_entity):
		current_entity.queue_free()
	
	# 加载实体配置
	print("LiveLink: 加载配置: ", config_path)
	# 这里可以调用 EntityAssembler 来加载实体
	# 暂时只打印日志
