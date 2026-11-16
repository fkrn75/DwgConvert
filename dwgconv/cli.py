"""명령줄 인터페이스. 결과는 표준출력 JSON 한 개, 진단은 표준오류.

종료 코드: 0 전부 성공 / 1 일부 실패 / 2 사용법 오류 / 3 LibreDWG(또는 ezdxf) 없음.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .convert import DXF_VERSIONS, collect_inputs, convert_many
from .locate import find_dwg2dxf, libredwg_version
from .verify import ezdxf_available, verify_dxf


def _emit(obj) -> None:
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    sys.stdout.flush()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dwgconv", description="DWG를 DXF로 바꾸는 독립 도구(LibreDWG 사용)")
    p.add_argument("--version", action="version", version=f"dwgconv {__version__}")
    p.add_argument("--libredwg-dir", help="LibreDWG 폴더(dwg2dxf 위치)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="DWG(또는 폴더)를 DXF로 변환")
    c.add_argument("input", help="입력 .dwg 파일 또는 폴더")
    c.add_argument("-o", "--output", required=True, help="출력 폴더")
    c.add_argument("--dxf-version", choices=DXF_VERSIONS, help="저장할 DXF 버전")
    c.add_argument("--overwrite", action="store_true", help="기존 출력 덮어쓰기")
    c.add_argument("--timeout", type=float, default=300.0, help="파일당 제한 시간(초, 기본 300)")
    c.add_argument("--jobs", type=int, default=1, help="동시 변환 수(기본 1)")
    v = sub.add_parser("verify", help="DXF를 ezdxf로 열어 요약")
    v.add_argument("file", help=".dxf 파일")
    sub.add_parser("doctor", help="LibreDWG·ezdxf 상태 점검")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)  # 사용법 오류는 argparse가 종료 코드 2로 끝낸다
    if args.cmd == "doctor":
        exe, how = find_dwg2dxf(args.libredwg_dir)
        _emit({"dwgconv": __version__,
               "libredwg": {"found": exe is not None, "path": str(exe) if exe else None,
                            "via": how or None, "version": libredwg_version(exe) if exe else None},
               "ezdxf": ezdxf_available()})
        return 0 if exe else 3
    if args.cmd == "verify":
        if not ezdxf_available():
            print("ezdxf가 없습니다: pip install ezdxf", file=sys.stderr)
            return 3
        f = Path(args.file)
        if not f.is_file():
            print(f"파일이 없습니다: {f}", file=sys.stderr)
            return 2
        r = verify_dxf(f)
        _emit(r)
        return 0 if r["ok"] else 1
    # convert
    src = Path(args.input)
    if not src.exists():
        print(f"입력이 없습니다: {src}", file=sys.stderr)
        return 2
    if src.is_file() and src.suffix.lower() != ".dwg":
        print("입력은 .dwg 파일 또는 폴더여야 합니다", file=sys.stderr)
        return 2
    if args.jobs < 1 or args.timeout <= 0:
        print("--jobs는 1 이상, --timeout은 0보다 커야 합니다", file=sys.stderr)
        return 2
    exe, how = find_dwg2dxf(args.libredwg_dir)
    if exe is None:
        print("LibreDWG(dwg2dxf)를 찾지 못했습니다. tools/fetch_libredwg.py 를 실행하거나 --libredwg-dir 를 지정하세요",
              file=sys.stderr)
        return 3
    if not collect_inputs(src):
        print("변환할 DWG가 없습니다", file=sys.stderr)
        return 2
    results = convert_many(exe, src, Path(args.output), dxf_version=args.dxf_version,
                           overwrite=args.overwrite, timeout=args.timeout, jobs=args.jobs)
    ok = sum(1 for r in results if r["ok"])
    _emit({"libredwg": libredwg_version(exe), "total": len(results), "succeeded": ok,
           "failed": len(results) - ok, "files": results})
    return 0 if ok == len(results) else 1
