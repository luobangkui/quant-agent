from __future__ import annotations

import yaml
from pathlib import Path

from core.data.provider import ProviderConfig, RetryConfig, ThrottleConfig


def load_raw_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_provider_config(raw: dict, provider_name: str) -> ProviderConfig:
    providers = raw.get("providers", {})
    if provider_name not in providers:
        raise ValueError(f"未找到 provider 配置: {provider_name}")
    cfg = providers[provider_name]
    throttle_cfg = cfg.get("throttle", {}) or {}
    retry_cfg = cfg.get("retry", {}) or {}
    return ProviderConfig(
        username=cfg.get("username"),
        password=cfg.get("password"),
        base_dir=Path(cfg.get("base_dir", "/share/quant/data")),
        timezone=cfg.get("timezone", "Asia/Shanghai"),
        throttle=ThrottleConfig(
            max_per_minute=int(throttle_cfg.get("max_per_minute", 60)),
            burst=int(throttle_cfg.get("burst", 5)),
        ),
        retry=RetryConfig(
            max_attempts=int(retry_cfg.get("max_attempts", 3)),
            backoff_seconds=float(retry_cfg.get("backoff_seconds", 1.0)),
        ),
    )
