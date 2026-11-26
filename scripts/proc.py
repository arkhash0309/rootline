"""Subprocess helper used by every Taskfile script (GEN-041)."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    env: Mapping[str, str] | None = None,
    timeout: int = 600,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **(env or {})}
    # S603: `cmd` is a list passed without a shell; every caller is a repository script (GEN-041).
    return subprocess.run(  # noqa: S603
        cmd, check=check, capture_output=capture, text=True, env=full_env, timeout=timeout, input=input_text
    )
