from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import (
    user_cache_dir,
    user_config_dir,
    user_log_dir,
    user_state_dir,
    user_runtime_dir,
)

from .context import RuntimeContext


@dataclass(frozen=True)
class AppPaths:
    config_dir: Path   # encrypted config files
    state_dir: Path    # token caches, durable state, keys
    cache_dir: Path    # ephemeral cache
    logs_dir: Path     # logs

    def ensure(self) -> "AppPaths":
        for d in (self.config_dir, self.state_dir, self.cache_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self


def resolve_paths(ctx: RuntimeContext) -> AppPaths:
    """
    Uses platformdirs. If ctx.profile != 'default', we nest under that profile.
    If ctx.root_override is set, we use that as a base and create subfolders ourselves.
    """
    profile_suffix = "" if ctx.profile == "default" else f"profiles/{ctx.profile}"

    if ctx.root_override:
        base = ctx.root_override
        config_dir = base / "config" / profile_suffix
        state_dir = base / "state" / profile_suffix
        cache_dir = base / "cache" / profile_suffix
        logs_dir = base / "logs"
        return AppPaths(config_dir, state_dir, cache_dir, logs_dir)

    # platformdirs gives canonical per-user locations
    config_base = Path(user_config_dir(ctx.app_name, appauthor=False))
    state_base  = Path(user_state_dir(ctx.app_name, appauthor=False))
    cache_base  = Path(user_cache_dir(ctx.app_name, appauthor=False))
    logs_base   = Path(user_log_dir(ctx.app_name, appauthor=False))

    config_dir = config_base / profile_suffix
    state_dir  = state_base / profile_suffix
    cache_dir  = cache_base / profile_suffix
    logs_dir   = logs_base  # typically not per-profile, but you can if you want

    return AppPaths(config_dir, state_dir, cache_dir, logs_dir)


def resolve_dry_run_out_dir() -> Path:
    return Path(user_runtime_dir("send")) / "dry_run"
