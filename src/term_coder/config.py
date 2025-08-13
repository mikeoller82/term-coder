from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


CONFIG_DIR = Path(".term-coder")
CONFIG_PATH = CONFIG_DIR / "config.yaml"


DEFAULT_CONFIG: Dict[str, Any] = {
    "model": {
        "default": "gpt-5-mini",
        "heavy": "gpt-5",
        "local": "ollama/gpt-oss"
    },
    "retrieval": {
        "max_files": 50,
        "max_tokens": 8000,
        "hybrid_weight": 0.7,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "embedding": {
            "backend": "hash",  # one of: hash | sentence-transformers | openai
            "model": "all-MiniLM-L6-v2",  # used when backend != hash
            "openai_model": "text-embedding-3-small",  # optional override for OpenAI backend
        },
    },
    "safety": {
        "require_confirmation": True,
        "create_backups": True,
        "max_file_size": 1_048_576,
    },
    "privacy": {
        "offline": False,
        "redact_secrets": True,
        "log_prompts": False,
    },
    "sandbox": {
        "cpu_seconds": 5,
        "memory_mb": 512,
        "no_network": False,
    },
    "git": {
        "create_branch_on_edit": False,
        "auto_stage_patches": True,
        "commit_message_template": "AI: {summary}",
    },
    "formatters": {
        "python": ["black", "isort"],
        "javascript": ["prettier"],
        "go": ["gofmt"],
    },
}


@dataclass
class Config:
    data: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG.copy())

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(str(CONFIG_PATH))
        loaded = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        return cls(merge_dicts(DEFAULT_CONFIG, loaded))

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(self.to_yaml())

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.data, sort_keys=False)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        node = self.data
        for part in dotted_key.split('.'):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        old_value = self.get(dotted_key)
        node = self.data
        parts = dotted_key.split('.')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = coerce_value(value)
        
        # Log configuration change if audit logger is available
        try:
            from .audit import create_audit_logger
            from .security import create_privacy_manager
            
            config_dir = Path(".term-coder")
            if config_dir.exists():
                privacy_manager = create_privacy_manager(config_dir)
                audit_logger = create_audit_logger(config_dir, privacy_manager)
                audit_logger.log_config_change(dotted_key, old_value, value)
        except Exception:
            # Silently ignore audit logging errors to avoid breaking config updates
            pass


def ensure_initialized() -> Path:
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    cfg = Config()
    cfg.save()
    return CONFIG_PATH


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            result[key] = merge_dicts(base[key], value)
        else:
            result[key] = value
    return result


def coerce_value(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value

