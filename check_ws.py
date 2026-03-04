import asyncio
import json
import websockets

WS_URL = "ws://localhost:8000/ws"


async def test_websocket():
    print(f"尝试连接到: {WS_URL}")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket 连接成功!")

            # 接收服务器消息
            print("\n等待接收广播消息...")

            # 设置超时，接收几条消息
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    print(f"\n📩 收到消息 #{i+1}:")
                    print(f"   {message}")

                    # 解析 JSON
                    try:
                        data = json.loads(message)
                        print(f"   解析后: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    except json.JSONDecodeError as e:
                        print(f"   JSON 解析失败: {e}")

                except asyncio.TimeoutError:
                    print("\n⏱ 等待超时 (10秒无新消息)")
                    break

            # 发送测试消息
            print("\n" + "="*50)
            print("发送测试消息到服务器...")
            test_msg = {"action": "ping", "client": "test-python"}
            await websocket.send(json.dumps(test_msg))
            print(f"✅ 已发送: {test_msg}")

            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📩 服务器响应: {response}")
            except asyncio.TimeoutError:
                print("⏱ 等待响应超时")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ 连接关闭: {e}")
    except ConnectionRefusedError:
        print("❌ 连接被拒绝 - 请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 连接失败: {e}")


async def send_broadcast_message():
    """直接发送 spawn_entity 广播消息来测试"""
    print(f"\n连接到服务器发送测试广播...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ 连接成功!")

            # 模拟 generate_entity 生成的广播
            broadcast_msg = {
                "action": "spawn_entity",
                "config_path": "D:\\code\\Agent_Game\\godot_project\\configs\\test_entity.json",
                "entity_name": "TestEntity"
            }

            await websocket.send(json.dumps(broadcast_msg))
            print(f"✅ 已发送广播消息:")
            print(f"   {json.dumps(broadcast_msg, indent=2, ensure_ascii=False)}")

    except Exception as e:
        print(f"❌ 失败: {e}")


if __name__ == "__main__":
    import sys

    print("="*50)
    print("WebSocket 测试工具")
    print("="*50)

    if len(sys.argv) > 1 and sys.argv[1] == "broadcast":
        asyncio.run(send_broadcast_message())
    else:
        asyncio.run(test_websocket())
