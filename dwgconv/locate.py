"""LibreDWG 설치 위치 탐색. 순서: 인자 -> 환경변수 LIBREDWG_DIR -> vendor/libredwg -> PATH."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

EXE = "dwg2dxf.exe" if os.name == "nt" else "dwg2dxf"
# 저장소 루트(= 이 패키지의 상위 폴더)
REPO_ROOT = Path(__file__).resolve().parent.parent


def _in_dir(d: Path) -> Path | None:
    """폴더 안(또는 bin 하위)에 dwg2dxf 실행 파일이 있으면 경로 반환."""
    for cand in (d / EXE, d / "bin" / EXE):
        if cand.is_file():
            return cand
    return None


def find_dwg2dxf(libredwg_dir: str | None = None) -> tuple[Path | None, str]:
    """(실행파일 경로, 찾은 방법) 반환. 못 찾으면 (None, '')."""
    if libredwg_dir:
        p = _in_dir(Path(libredwg_dir))
        return (p, "--libredwg-dir") if p else (None, "")
    env = os.environ.get("LIBREDWG_DIR")
    if env:
        p = _in_dir(Path(env))
        if p:
            return p, "LIBREDWG_DIR"
    p = _in_dir(REPO_ROOT / "vendor" / "libredwg")
    if p:
        return p, "vendor"
    w = shutil.which("dwg2dxf")
    if w:
        return Path(w), "PATH"
    return None, ""


def libredwg_version(exe: Path) -> str | None:
    """dwg2dxf --version 첫 줄에서 버전 문자열 추출."""
    try:
        r = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=20)
        line = (r.stdout or r.stderr).strip().splitlines()
        return line[0].strip() if line else None
    except Exception:
        return None
