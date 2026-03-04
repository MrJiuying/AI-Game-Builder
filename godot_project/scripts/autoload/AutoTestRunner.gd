class_name AutoTestRunner
extends Node2D

## 自动集成测试运行器 - 全自动执行 AI 游戏组装闭环测试
##
## 使用方法：
## 1. 在 Godot 中创建一个新场景
## 2. 添加一个 Node2D 根节点
## 3. 将此脚本挂载到根节点
## 4. 运行游戏，自动执行全部测试流程

const CONFIG_DIR: String = "res://configs/"
const COMPONENTS_DIR: String = "res://components/"
const SPRITES_DIR: String = "res://assets/sprites/"
const ASSEMBLER_PATH: String = "res://scripts/autoload/EntityAssembler.gd"

var _test_results: Dictionary = {}
var _assembler: Node = null


func _ready() -> void:
	print_rich("[color=#00FF00][b]========== 自动集成测试开始 ==========[/b][/color]")
	
	await get_tree().process_frame
	
	_run_all_tests()
	
	_print_summary()


func _run_all_tests() -> void:
	_test_results["environment_setup"] = _test_environment_setup()
	
	_test_results["mock_data_generation"] = _test_mock_data_generation()
	
	_test_results["component_fallback"] = _test_component_fallback()
	
	_test_results["entity_assembly"] = await _test_entity_assembly()


func _test_environment_setup() -> bool:
	print_rich("\n[color=#00FFFF][b]▶ 测试 1: 环境自检与自动修复[/b][/color]")
	
	var dirs: Array[String] = [CONFIG_DIR, COMPONENTS_DIR, SPRITES_DIR]
	var all_success: bool = true
	
	for dir_path in dirs:
		if DirAccess.dir_exists_absolute(dir_path):
			print_rich("  [color=#90EE90]✓[/color] 目录已存在: %s" % dir_path)
		else:
			var error = DirAccess.make_dir_recursive_absolute(dir_path)
			if error == OK:
				print_rich("  [color=#FFA500]✓[/color] 目录已自动创建: %s" % dir_path)
			else:
				print_rich("  [color=#FF6B6B]✗[/color] 目录创建失败: %s" % dir_path)
				all_success = false
	
	return all_success


func _test_mock_data_generation() -> bool:
	print_rich("\n[color=#00FFFF][b]▶ 测试 2: 自动生成测试资产[/b][/color]")
	
	var json_content: String = JSON.stringify({
		"entity_name": "TestPlayer",
		"base_type": "CharacterBody2D",
		"components": ["VelocityComponent", "HealthComponent"],
		"component_params": {
			"VelocityComponent": {
				"max_speed": 500.0,
				"acceleration": 1000.0,
				"friction": 800.0
			},
			"HealthComponent": {
				"max_health": 100.0
			}
		},
		"sprite_path": "res://icon.svg"
	}, "\t")
	
	var test_json_path: String = CONFIG_DIR + "test_player.json"
	
	var file: FileAccess = FileAccess.open(test_json_path, FileAccess.WRITE)
	if file == null:
		print_rich("  [color=#FF6B6B]✗[/color] JSON 文件创建失败: %s" % test_json_path)
		return false
	
	file.store_string(json_content)
	file.close()
	
	print_rich("  [color=#90EE90]✓[/color] 测试 JSON 已生成: %s" % test_json_path)
	print_rich("  [color=#AAAAAA]  └─ 实体: TestPlayer, max_speed: 500.0[/color]")
	
	return true


func _test_component_fallback() -> bool:
	print_rich("\n[color=#00FFFF][b]▶ 测试 3: 检查并生成缺失组件[/b][/color]")
	
	var required_components: Array[String] = ["VelocityComponent.gd", "HealthComponent.gd"]
	var all_success: bool = true
	
	for comp_file in required_components:
		var comp_path: String = COMPONENTS_DIR + comp_file
		
		if FileAccess.file_exists(comp_path):
			print_rich("  [color=#90EE90]✓[/color] 组件已存在: %s" % comp_file)
		else:
			if _create_placeholder_component(comp_file):
				print_rich("  [color=#FFA500]✓[/color] 组件已自动生成: %s" % comp_file)
			else:
				print_rich("  [color=#FF6B6B]✗[/color] 组件生成失败: %s" % comp_file)
				all_success = false
	
	return all_success


func _create_placeholder_component(comp_name: String) -> bool:
	var script_content: String = ""
	var class_name: String = comp_name.get_file().get_basename()
	
	match class_name:
		"VelocityComponent":
			script_content = """extends Node
class_name VelocityComponent

@export var max_speed: float = 300.0
@export var acceleration: float = 1000.0
@export var friction: float = 800.0
"""
		"HealthComponent":
			script_content = """extends Node
class_name HealthComponent

signal health_changed(previous_health: float, current_health: float)
signal died()

@export var max_health: float = 100.0
var current_health: float = max_health
"""
		_:
			script_content = """extends Node
class_name %s
""" % class_name
	
	var file: FileAccess = FileAccess.open(COMPONENTS_DIR + comp_name, FileAccess.WRITE)
	if file == null:
		return false
	
	file.store_string(script_content)
	file.close()
	
	return true


func _test_entity_assembly() -> bool:
	print_rich("\n[color=#00FFFF][b]▶ 测试 4: 自动执行装配与渲染[/b][/color]")
	
	if not _load_or_create_assembler():
		return false
	
	var test_json_path: String = CONFIG_DIR + "test_player.json"
	
	if not FileAccess.file_exists(test_json_path):
		print_rich("  [color=#FF6B6B]✗[/color] 测试 JSON 不存在: %s" % test_json_path)
		return false
	
	var build_method: Callable
	if _assembler.has_method("build_entity_from_json"):
		build_method = _assembler.build_entity_from_json
	elif _assembler.has_method("build_entity_from_dict"):
		build_method = _assembler.build_entity_from_dict
	else:
		print_rich("  [color=#FF6B6B]✗[/color] EntityAssembler 缺少 build 方法")
		return false
	
	var entity: Node2D = null
	
	if build_method == _assembler.build_entity_from_json:
		entity = _assembler.build_entity_from_json(test_json_path)
	
	if entity == null:
		print_rich("  [color=#FF6B6B]✗[/color] 实体装配失败")
		return false
	
	entity.position = Vector2(500, 300)
	add_child(entity)
	
	print_rich("  [color=#90EE90]✓[/color] 实体装配成功!")
	print_rich("  [color=#AAAAAA]  └─ 实体名称: %s" % entity.name)
	print_rich("  [color=#AAAAAA]  └─ 实体类型: %s" % entity.get_class())
	print_rich("  [color=#AAAAAA]  └─ 子节点数量: %d" % entity.get_child_count())
	print_rich("  [color=#AAAAAA]  └─ 屏幕位置: %s" % str(entity.position))
	
	for child in entity.get_children():
		if child is Node:
			print_rich("  [color=#AAAAAA]     ├─ 子节点: %s (%s)" % [child.name, child.get_class()])
	
	return true


func _load_or_create_assembler() -> bool:
	if FileAccess.file_exists(ASSEMBLER_PATH):
		var assembler_script: GDScript = load(ASSEMBLER_PATH)
		if assembler_script != null:
			_assembler = assembler_script.new()
			print_rich("  [color=#90EE90]✓[/color] EntityAssembler 加载成功")
			return true
	
	print_rich("  [color=#FFA500]⚠[/color] EntityAssembler 不存在，使用内置简化版本")
	
	_assembler = _create_fallback_assembler()
	return _assembler != null


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


func _print_summary() -> void:
	print_rich("\n[color=#00FF00][b]========== 测试结果汇总 ==========[/b][/color]")
	
	var total: int = _test_results.size()
	var passed: int = 0
	
	for test_name in _test_results:
		var result: bool = _test_results[test_name]
		if result:
			passed += 1
			print_rich("  [color=#90EE90]✓[/color] %s" % test_name)
		else:
			print_rich("  [color=#FF6B6B]✗[/color] %s" % test_name)
	
	print_rich("\n[color=#00FFFF]通过: %d / %d[/color]" % [passed, total])
	
	if passed == total:
		print_rich("\n[color=#00FF00][b]🎉 所有测试通过! 实体已显示在屏幕中央 (500, 300)[/b][/color]")
	else:
		print_rich("\n[color=#FF6B6B][b]⚠ 部分测试失败，请检查日志[/b][/color]")
