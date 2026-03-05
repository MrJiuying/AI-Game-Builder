import argparse
import asyncio
import json
import mimetypes
import os
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "godot_project"
BUILD_DIR = ROOT_DIR / "web_build"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--godot-path", default="")
    parser.add_argument("--preset", default="Web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8060)
    parser.add_argument("--backend-ws", default="ws://127.0.0.1:8000/ws")
    parser.add_argument("--skip-export", action="store_true")
    return parser.parse_args()


def resolve_godot_executable(cli_path: str) -> str:
    if cli_path and Path(cli_path).exists():
        return cli_path
    env_candidates = [
        os.getenv("GODOT_PATH", "").strip(),
        os.getenv("GODOT_EXE_PATH", "").strip(),
        os.getenv("GODOT_EXE", "").strip(),
    ]
    for candidate in env_candidates:
        if candidate and Path(candidate).exists():
            return candidate
    which_candidates = [
        shutil.which("godot"),
        shutil.which("godot4"),
        shutil.which("Godot_v4"),
    ]
    for candidate in which_candidates:
        if candidate:
            return candidate
    raise RuntimeError(
        "找不到 Godot CLI。请配置环境变量 GODOT_PATH 或 GODOT_EXE_PATH，"
        "例如：setx GODOT_PATH \"D:\\\\Softwares\\\\Godot\\\\Godot_v4.3-stable_win64.exe\""
    )


def ensure_export_preset(preset_name: str) -> None:
    preset_file = PROJECT_DIR / "export_presets.cfg"
    if not preset_file.exists():
        raise RuntimeError(
            f"未找到 {preset_file}。请先在 Godot 编辑器中配置 HTML5 导出预设（建议命名为 {preset_name}）。"
        )
    text = preset_file.read_text(encoding="utf-8", errors="ignore")
    if f'name="{preset_name}"' not in text:
        raise RuntimeError(
            f"未在 export_presets.cfg 中找到预设 {preset_name}。请在 Godot 导出面板中创建同名预设。"
        )


def run_web_export(godot_exe: str, preset_name: str) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    output_html = BUILD_DIR / "index.html"
    cmd = [
        godot_exe,
        "--headless",
        "--path",
        str(PROJECT_DIR),
        "--export-release",
        preset_name,
        str(output_html),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Godot Web 导出失败。\n"
            f"命令: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    if not output_html.exists():
        raise RuntimeError("导出完成但未生成 index.html。")
    wasm_files = list(BUILD_DIR.glob("*.wasm"))
    if not wasm_files:
        raise RuntimeError("导出目录缺少 .wasm 文件，请检查 HTML5 导出模板是否安装完整。")
    return output_html


def create_handler(directory: Path):
    class StageRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            return

        def end_headers(self):
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
            super().end_headers()

    return StageRequestHandler


async def send_engine_ready(ws_url: str, stage_url: str) -> None:
    try:
        import websockets
    except Exception:
        print("未安装 websockets，跳过 engine_ready 信号发送。可执行: pip install websockets")
        return

    payload = {
        "action": "engine_ready",
        "source": "run_stage.py",
        "stage_url": stage_url,
    }
    try:
        async with websockets.connect(ws_url) as websocket:
            await websocket.send(json.dumps(payload, ensure_ascii=False))
        print(f"已发送 engine_ready 到 {ws_url}")
    except Exception as exc:
        print(f"发送 engine_ready 失败: {exc}")


def start_server(host: str, port: int) -> None:
    mimetypes.add_type("application/wasm", ".wasm")
    handler = create_handler(BUILD_DIR)
    server = ThreadingHTTPServer((host, port), handler)
    stage_url = f"http://{host}:{port}"
    print(f"Godot Web 服务已启动: {stage_url}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> None:
    args = parse_args()
    if not PROJECT_DIR.exists():
        raise RuntimeError(f"未找到 Godot 工程目录: {PROJECT_DIR}")

    if not args.skip_export:
        godot_exe = resolve_godot_executable(args.godot_path)
        ensure_export_preset(args.preset)
        output_html = run_web_export(godot_exe, args.preset)
        print(f"导出完成: {output_html}")
    else:
        if not (BUILD_DIR / "index.html").exists():
            raise RuntimeError("--skip-export 已启用，但 web_build/index.html 不存在。")

    stage_url = f"http://{args.host}:{args.port}"
    asyncio.run(send_engine_ready(args.backend_ws, stage_url))
    start_server(args.host, args.port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("已停止 Godot Web 服务。")
        sys.exit(0)
    except Exception as exc:
        print(f"[run_stage] 错误: {exc}")
        sys.exit(1)
