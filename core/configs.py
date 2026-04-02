"""
DeskBot - Configuration

Loads settings from .env file in the project root.

Usage:
    from core.configs import config

    print(config.OLLAMA_HOST)
    print(config.OLLAMA_MODEL)
"""

import os
from pathlib import Path


def _load_env(env_path: Path) -> None:
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key not in os.environ:
                    os.environ[key] = value


class Config:
    def __init__(self):
        # Walk up from core/ to find .env at project root
        project_root = Path(__file__).parent.parent
        _load_env(project_root / ".env")

    @property
    def OLLAMA_HOST(self) -> str:
        return os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    @property
    def OLLAMA_MODEL(self) -> str:
        return os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

    @property
    def DISPLAY_WIDTH(self) -> int:
        return int(os.environ.get("DISPLAY_WIDTH", "1080"))

    @property
    def DISPLAY_HEIGHT(self) -> int:
        return int(os.environ.get("DISPLAY_HEIGHT", "1080"))

    @property
    def FULLSCREEN(self) -> bool:
        return os.environ.get("FULLSCREEN", "false").lower() == "true"

    @property
    def LOG_LEVEL(self) -> str:
        return os.environ.get("LOG_LEVEL", "DEBUG")


config = Config()