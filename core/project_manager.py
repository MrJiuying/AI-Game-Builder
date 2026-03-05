from pathlib import Path
from typing import Optional, Union
import shutil
import logging
import uuid
import os


logger = logging.getLogger(__name__)


class ProjectResourceManager:
    def __init__(self, godot_project_path: str):
        self._project_root = Path(godot_project_path)
        self._sprites_dir = self._project_root / "assets" / "sprites"
        self._scenes_dir = self._project_root / "scenes"
        self._scripts_dir = self._project_root / "scripts"
        self._ensure_directories()
    
    @property
    def project_root(self) -> Path:
        """获取工程根目录"""
        return self._project_root

    def _ensure_directories(self) -> None:
        self._sprites_dir.mkdir(parents=True, exist_ok=True)
        self._scenes_dir.mkdir(parents=True, exist_ok=True)
        self._scripts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"资源目录已确认: {self._sprites_dir}")
        logger.info(f"场景目录已确认: {self._scenes_dir}")
        logger.info(f"脚本目录已确认: {self._scripts_dir}")

    def save_sprite(
        self, 
        source_path: Union[str, Path], 
        target_name: Optional[str] = None
    ) -> str:
        source = Path(source_path)
        
        if not source.exists():
            raise FileNotFoundError(f"源文件不存在: {source}")
        
        if target_name is None:
            target_name = source.name
        
        target_name = self._sanitize_filename(target_name)
        
        target_path = self._sprites_dir / target_name
        
        suffix = source.suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
            suffix = ".png"
            target_path = target_path.with_suffix(suffix)
        
        counter = 1
        original_stem = target_path.stem
        while target_path.exists():
            target_path = target_path.parent / f"{original_stem}_{counter}{target_path.suffix}"
            counter += 1
        
        shutil.copy2(source, target_path)
        
        godot_path = self._to_godot_path(target_path)
        logger.info(f"资源已保存: {source} -> {godot_path}")
        
        return godot_path

    async def save_generated_asset(self, image_bytes: bytes, entity_name: str) -> str:
        """保存生成的资产
        
        参数:
            image_bytes: 图片字节数据
            entity_name: 实体名称
            
        返回:
            str: Godot 格式的相对路径
        """
        target_name = f"{entity_name}_{uuid.uuid4().hex[:8]}.png"
        target_path = self._sprites_dir / target_name
        
        # 确保目录存在
        self._ensure_directories()
        
        # 保存图片
        with open(target_path, "wb") as f:
            f.write(image_bytes)
        
        godot_path = self._to_godot_path(target_path)
        logger.info(f"生成的资产已保存: {godot_path}")
        
        return godot_path

    def save_sprite_from_bytes(
        self, 
        image_bytes: bytes, 
        filename: str
    ) -> str:
        filename = self._sanitize_filename(filename)
        
        target_path = self._sprites_dir / filename
        
        suffix = Path(filename).suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
            suffix = ".png"
            target_path = target_path.with_suffix(suffix)
        
        counter = 1
        original_stem = target_path.stem
        while target_path.exists():
            target_path = target_path.parent / f"{original_stem}_{counter}{target_path.suffix}"
            counter += 1
        
        target_path.write_bytes(image_bytes)
        
        godot_path = self._to_godot_path(target_path)
        logger.info(f"资源已保存（字节流）: {godot_path}")
        
        return godot_path

    def _sanitize_filename(self, filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        
        filename = filename.strip(". ")
        
        if not filename:
            filename = "unnamed_asset"
        
        return filename

    def _to_godot_path(self, absolute_path: Path) -> str:
        try:
            relative = absolute_path.relative_to(self._project_root)
            return "res://" + str(relative).replace("\\", "/")
        except ValueError:
            return str(absolute_path).replace("\\", "/")

    def get_sprites_directory(self) -> str:
        return str(self._sprites_dir)

    def list_sprites(self) -> list[str]:
        if not self._sprites_dir.exists():
            return []
        
        extensions = [".png", ".jpg", ".jpeg", ".webp", ".svg"]
        sprites = []
        
        for ext in extensions:
            sprites.extend(self._sprites_dir.glob(f"*{ext}"))
        
        return [self._to_godot_path(p) for p in sorted(sprites)]
    
    def setup_preview_stage(self) -> dict:
        """设置预览场景
        
        返回:
            dict: 包含场景和脚本路径的信息
        """
        # 确保目录存在（使用绝对路径）
        scenes_dir = self._project_root / "scenes"
        scripts_dir = self._project_root / "scripts"
        
        os.makedirs(scenes_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)
        
        # 检查并创建 project.godot 文件
        project_godot_path = self._project_root / "project.godot"
        if not project_godot_path.exists():
            project_godot_content = """; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.
;
; Format:
;   [section] ; section goes between []
;   param=value ; assign values to parameters

[application]

config/name="AIGameBuilder_Preview"
run/main_scene="res://scenes/PreviewStage.tscn"
config/features=PackedStringArray("4.3", "Forward Plus")

[rendering]

renderer/rendering_method="forward_plus"
"""
            project_godot_path.write_text(project_godot_content, encoding="utf-8")
            logger.info(f"project.godot 已创建: {project_godot_path}")
        
        logger.info(f"场景目录: {scenes_dir}")
        logger.info(f"脚本目录: {scripts_dir}")
        
        # 写入 PreviewStage.tscn（修正路径引用）
        tscn_content = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/LiveLink.gd" id="1_link"]

[node name="PreviewStage" type="Node2D"]
script = ExtResource("1_link")

[node name="Camera2D" type="Camera2D" parent="."]
position = Vector2(576, 324)
"""
        tscn_path = scenes_dir / "PreviewStage.tscn"
        tscn_path.write_text(tscn_content, encoding="utf-8")
        logger.info(f"预览场景已创建: {tscn_path}")
        
        # 写入 LiveLink.gd
        livelink_content = '''extends Node2D

var socket = WebSocketPeer.new()
var websocket_url = "ws://127.0.0.1:8000/ws"
var was_connected = false
var current_entity: Node2D = null

func _ready():
	print("【LiveLink】🚀 准备连接到中枢大脑: ", websocket_url)
	var err = socket.connect_to_url(websocket_url)
	if err != OK:
		print("【LiveLink】❌ 初始连接请求失败，错误码: ", err)

func _process(delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not was_connected:
			print("【LiveLink】🟢 已成功连入 AI 中枢！等待指令...")
			was_connected = true
		
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			var msg = packet.get_string_from_utf8()
			print("【LiveLink】📩 收到神谕: ", msg.substr(0, 60), "...")
			handle_message(msg)
			
	elif state == WebSocketPeer.STATE_CLOSED:
		if was_connected:
			print("【LiveLink】🔴 连接断开，尝试重连...")
			was_connected = false
		socket.connect_to_url(websocket_url)

func handle_message(msg: String):
	print("【LiveLink】📦 开始拆解神谕快递...")
	var data = JSON.parse_string(msg)
	if data == null:
		print("【LiveLink】❌ JSON 解析失败！收到的字符串有问题。")
		return
	
	if not data is Dictionary:
		print("【LiveLink】❌ 解析结果不是字典！")
		return
	
	var action = data.get("action", "")
	if action == "spawn_entity":
		spawn_entity(data)
	else:
		print("【LiveLink】⚠️ 未知 action: ", action)

func spawn_entity(data: Dictionary):
	print("【LiveLink】🏗️ 开始装配实体...")
	
	var config_path = data.get("config_path", "")
	var sprite_path = data.get("sprite_path", "")
	
	if config_path == "":
		print("【LiveLink】❌ 消息中没有 config_path，无法装配！")
		return
	
	var global_config_path = ProjectSettings.globalize_path(config_path)
	if not FileAccess.file_exists(global_config_path):
		print("【LiveLink】❌ 找不到图纸文件: ", global_config_path)
		return
	
	var file = FileAccess.open(global_config_path, FileAccess.READ)
	if file == null:
		print("【LiveLink】❌ 无法打开图纸文件: ", global_config_path)
		return
	
	var entity_data_text = file.get_as_text()
	file.close()
	
	if entity_data_text == "":
		print("【LiveLink】❌ 图纸文件内容为空！")
		return
	
	var entity_data = JSON.parse_string(entity_data_text)
	if entity_data == null:
		print("【LiveLink】❌ 图纸 JSON 解析失败！")
		return
	
	print("【LiveLink】✅ 图纸读取成功，准备构建实体！")
	
	# 1. 创建根节点
	if current_entity and is_instance_valid(current_entity):
		current_entity.queue_free()
	
	current_entity = CharacterBody2D.new()
	current_entity.name = "PreviewEntity"
	add_child(current_entity)
	
	# 2. 强力动态加载贴图
	var sprite = Sprite2D.new()
	sprite.name = "Sprite"
	var texture_loaded = false
	
	sprite_path = entity_data.get("sprite_path", "")
	if sprite_path != "":
		var real_img_path = ProjectSettings.globalize_path(sprite_path)
		print("【LiveLink】尝试加载图片: ", real_img_path)
		var img = Image.new()
		if img.load(real_img_path) == OK:
			sprite.texture = ImageTexture.create_from_image(img)
			texture_loaded = true
			sprite.scale = Vector2(0.25, 0.25)
			print("【LiveLink】✅ 成功加载 AI 专属立绘！")
		else:
			print("【LiveLink】❌ 立绘加载失败，路径: ", real_img_path)
	
	# 兜底贴图
	if not texture_loaded:
		print("【LiveLink】⚠️ 启用兜底蓝色机器人图标！")
		sprite.texture = load("res://icon.svg")
	
	# 设置精灵位置
	if sprite.texture != null:
		sprite.position = sprite.texture.get_size() / 2.0
	
	current_entity.add_child(sprite)
	
	# 3. 动态挂载组件
	var components = entity_data.get("components", [])
	var component_params = entity_data.get("component_params", {})
	print("【LiveLink】📋 需要挂载的组件: ", components)
	
	for comp_name in components:
		print("【LiveLink】🔧 尝试挂载组件: ", comp_name)
		var script_path = "res://components/" + comp_name + ".gd"
		if ResourceLoader.exists(script_path):
			var loaded_script = load(script_path)
			if loaded_script:
				var comp_node = loaded_script.new()
				comp_node.name = comp_name
				
				# 应用组件参数
				var params = component_params.get(comp_name, {})
				for param_key in params.keys():
					comp_node.set(param_key, params[param_key])
					print("【LiveLink】  设置参数 ", param_key, " = ", params[param_key])
				
				current_entity.add_child(comp_node)
				print("【LiveLink】✅ 组件 ", comp_name, " 挂载成功！")
			else:
				print("【LiveLink】❌ 组件脚本加载失败: ", script_path)
		else:
			print("【LiveLink】⚠️ 组件脚本不存在: ", script_path)
	
	# 4. 挂载到舞台并强制居中！
	current_entity.global_position = get_viewport_rect().size / 2.0
	print("【LiveLink】🎉 实体降临！坐标: ", current_entity.global_position)

func _create_fallback_sprite() -> Sprite2D:
	var sprite = Sprite2D.new()
	sprite.name = "FallbackSprite"
	sprite.texture = load("res://icon.svg")
	return sprite
'''
        livelink_path = scripts_dir / "LiveLink.gd"
        if livelink_path.exists():
            logger.info(f"LiveLink 脚本已存在，跳过覆盖: {livelink_path}")
        else:
            livelink_path.write_text(livelink_content, encoding="utf-8")
            logger.info(f"LiveLink 脚本已创建: {livelink_path}")
        
        return {
            "scene_path": str(tscn_path),
            "scene_godot_path": "res://scenes/PreviewStage.tscn",
            "script_path": str(livelink_path),
            "script_godot_path": "res://scripts/LiveLink.gd"
        }
    
    def get_project_path(self) -> str:
        """获取 Godot 工程路径
        
        返回:
            str: 工程绝对路径
        """
        return str(self._project_root)
