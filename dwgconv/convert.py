"""DWG -> DXF 변환 핵심. dwg2dxf를 하위 프로세스로만 호출한다(라이브러리 링크 없음)."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# DWG 파일 머리 6바이트 -> AutoCAD 버전 이름
DWG_VERSIONS = {
    "AC1009": "R11/R12", "AC1012": "R13", "AC1014": "R14", "AC1015": "2000",
    "AC1018": "2004", "AC1021": "2007", "AC1024": "2010", "AC1027": "2013",
    "AC1032": "2018",
}
DXF_VERSIONS = ["r12", "r14", "r2000", "r2004", "r2007", "r2010", "r2013", "r2018"]


def dwg_version(path: Path) -> str | None:
    """DWG 머리의 매직 문자열로 버전을 읽는다. 알 수 없으면 None."""
    try:
        with open(path, "rb") as f:
            magic = f.read(6).decode("ascii", "replace")
    except OSError:
        return None
    if not magic.startswith("AC"):
        return None
    return DWG_VERSIONS.get(magic, f"알 수 없음({magic})")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def collect_inputs(src: Path) -> list[tuple[Path, Path]]:
    """(DWG 경로, 입력 기준 상대 경로) 목록. 폴더면 하위 .dwg 재귀 수집(대소문자 무시)."""
    if src.is_file():
        return [(src, Path(src.name))]
    return [(p, p.relative_to(src)) for p in sorted(src.rglob("*"))
            if p.is_file() and p.suffix.lower() == ".dwg"]


def summarize_stderr(text: str) -> dict:
    """LibreDWG stderr를 경고/오류 개수와 대표 줄 몇 개로 요약."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    warn = [l for l in lines if re.search(r"warning", l, re.I)]
    err = [l for l in lines if re.search(r"error", l, re.I)]
    return {
        "lines": len(lines), "warnings": len(warn), "errors": len(err),
        "samples": (err[:3] + warn[:3])[:5],
    }


def convert_one(exe: Path, src: Path, rel: Path, out_dir: Path, *, dxf_version: str | None,
                overwrite: bool, timeout: float) -> dict:
    """DWG 1개 변환. 결과 dict 반환(예외를 던지지 않음)."""
    dst = out_dir / rel.with_suffix(".dxf")
    res = {"input": str(src), "output": str(dst), "ok": False, "error": None,
           "dwg_version": dwg_version(src), "input_bytes": None, "output_bytes": None,
           "sha256": None, "seconds": 0.0, "libredwg": None}
    t0 = time.monotonic()
    try:
        res["input_bytes"] = src.stat().st_size
        if dst.exists() and not overwrite:
            res["error"] = "출력 파일이 이미 있음(--overwrite 필요)"
            return res
        dst.parent.mkdir(parents=True, exist_ok=True)
        # dwg2dxf는 윈도에서 한글 경로를 못 다루므로 ASCII 임시 폴더에서 작업한다
        with tempfile.TemporaryDirectory(prefix="dwgconv_") as td:
            tdp = Path(td)
            shutil.copyfile(src, tdp / "in.dwg")
            cmd = [str(exe), "-y"]
            if dxf_version:
                cmd += ["--as", dxf_version]
            cmd += ["-o", "out.dxf", "in.dwg"]
            try:
                r = subprocess.run(cmd, cwd=td, capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                res["error"] = f"시간 초과({timeout}초)"
                return res
            err_txt = (r.stderr or b"").decode("utf-8", "replace") + (r.stdout or b"").decode("utf-8", "replace")
            res["libredwg"] = {"exit_code": r.returncode, **summarize_stderr(err_txt)}
            tmp_out = tdp / "out.dxf"
            if not tmp_out.is_file() or tmp_out.stat().st_size == 0:
                res["error"] = f"dwg2dxf가 DXF를 만들지 못함(종료 코드 {r.returncode})"
                return res
            # 종료 코드 128 이상 = LibreDWG 치명 오류. 파일이 있어도 불완전할 수 있다
            if r.returncode >= 128:
                res["error"] = f"LibreDWG 치명 오류(종료 코드 {r.returncode}); 출력 불완전 가능"
                return res
            shutil.move(str(tmp_out), dst)
        res["output_bytes"] = dst.stat().st_size
        res["sha256"] = sha256_of(dst)
        res["ok"] = True
    except Exception as e:  # 파일별 실패가 전체를 막지 않게
        res["error"] = f"{type(e).__name__}: {e}"
    finally:
        res["seconds"] = round(time.monotonic() - t0, 3)
    return res


def convert_many(exe: Path, src: Path, out_dir: Path, *, dxf_version=None, overwrite=False,
                 timeout=300.0, jobs=1) -> list[dict]:
    items = collect_inputs(src)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = [ex.submit(convert_one, exe, s, r, out_dir, dxf_version=dxf_version,
                          overwrite=overwrite, timeout=timeout) for s, r in items]
        return [f.result() for f in futs]
