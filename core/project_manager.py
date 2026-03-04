from pathlib import Path
from typing import Optional, Union
import shutil
import logging


logger = logging.getLogger(__name__)


class ProjectResourceManager:
    def __init__(self, godot_project_path: str):
        self._project_root = Path(godot_project_path)
        self._sprites_dir = self._project_root / "assets" / "sprites"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self._sprites_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"资源目录已确认: {self._sprites_dir}")

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
