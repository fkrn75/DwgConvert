"""dwgconv 시험. 견본/LibreDWG가 없어도 도는 시험과, 있으면 도는 실변환 시험으로 나뉜다."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
sys.path.insert(0, str(ROOT))

from dwgconv import cli  # noqa: E402
from dwgconv.convert import collect_inputs, dwg_version, summarize_stderr  # noqa: E402
from dwgconv.locate import find_dwg2dxf  # noqa: E402
from dwgconv.verify import ezdxf_available  # noqa: E402

EXE, _ = find_dwg2dxf()
need_lib = pytest.mark.skipif(EXE is None, reason="LibreDWG 없음")
DWGS = sorted(SAMPLES.glob("*.dwg"))


def run(*args, env=None):
    e = dict(os.environ)
    e.pop("LIBREDWG_DIR", None)
    e.update(env or {})
    return subprocess.run([sys.executable, "-m", "dwgconv", *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", env=e)


def test_사용법_오류는_종료코드_2():
    assert run().returncode == 2
    assert run("convert", "x.dwg").returncode == 2  # -o 누락


def test_없는_입력은_2(tmp_path):
    assert run("convert", str(tmp_path / "없음.dwg"), "-o", str(tmp_path)).returncode == 2


def test_LibreDWG_없으면_3(tmp_path):
    f = tmp_path / "a.dwg"
    f.write_bytes(b"AC1015" + b"\0" * 64)
    r = run("--libredwg-dir", str(tmp_path / "없는폴더"), "convert", str(f), "-o", str(tmp_path / "o"))
    assert r.returncode == 3
    d = run("--libredwg-dir", str(tmp_path / "없는폴더"), "doctor")
    assert d.returncode == 3 and json.loads(d.stdout)["libredwg"]["found"] is False


def test_폴더_수집은_재귀_대소문자무시(tmp_path):
    (tmp_path / "하위").mkdir()
    (tmp_path / "하위" / "A.DWG").write_bytes(b"x")
    (tmp_path / "b.dwg").write_bytes(b"x")
    (tmp_path / "c.txt").write_bytes(b"x")
    rels = sorted(r.as_posix() for _, r in collect_inputs(tmp_path))
    assert rels == ["b.dwg", "하위/A.DWG"]


def test_버전_매직(tmp_path):
    f = tmp_path / "v.dwg"
    f.write_bytes(b"AC1032....")
    assert dwg_version(f) == "2018"
    f.write_bytes(b"ZZZZZZ")
    assert dwg_version(f) is None


def test_stderr_요약():
    s = summarize_stderr("Warning: a\nERROR: b\n\nWarning: c\n")
    assert (s["warnings"], s["errors"], s["lines"]) == (2, 1, 3)


def test_가짜_dwg는_실패로_보고_JSON_형식(tmp_path):
    """LibreDWG가 있을 때, 깨진 DWG는 종료 코드 1이고 JSON에 error가 있다."""
    if EXE is None:
        pytest.skip("LibreDWG 없음")
    f = tmp_path / "깨짐.dwg"
    f.write_bytes(b"AC1015" + b"\x01" * 200)
    r = run("convert", str(f), "-o", str(tmp_path / "out"))
    assert r.returncode == 1
    j = json.loads(r.stdout)
    assert j["total"] == 1 and j["failed"] == 1
    item = j["files"][0]
    assert item["ok"] is False and item["error"]
    for k in ("input", "output", "input_bytes", "sha256", "seconds", "dwg_version", "libredwg"):
        assert k in item


@need_lib
def test_타임아웃(tmp_path):
    f = tmp_path / "t.dwg"
    f.write_bytes(b"AC1015" + b"\0" * 64)
    r = run("convert", str(f), "-o", str(tmp_path / "o"), "--timeout", "0.001")
    assert r.returncode == 1
    assert "시간 초과" in json.loads(r.stdout)["files"][0]["error"]


@need_lib
def test_doctor():
    r = run("doctor")
    assert r.returncode == 0
    assert json.loads(r.stdout)["libredwg"]["found"] is True


@need_lib
@pytest.mark.skipif(not DWGS, reason="견본 없음(tools/fetch_samples.py)")
@pytest.mark.parametrize("dwg", DWGS, ids=lambda p: p.name)
def test_견본_변환과_verify(dwg, tmp_path):
    r = run("convert", str(dwg), "-o", str(tmp_path))
    j = json.loads(r.stdout)
    item = j["files"][0]
    assert item["ok"], item["error"]
    assert r.returncode == 0 and len(item["sha256"]) == 64 and item["output_bytes"] > 0
    # 덮어쓰기 없이 다시 돌리면 실패, --overwrite면 성공
    assert run("convert", str(dwg), "-o", str(tmp_path)).returncode == 1
    assert run("convert", str(dwg), "-o", str(tmp_path), "--overwrite").returncode == 0
    if ezdxf_available():
        v = run("verify", item["output"])
        assert v.returncode == 0, v.stdout
        vj = json.loads(v.stdout)
        assert vj["ok"] and vj["layers"] >= 1


@need_lib
@pytest.mark.skipif(len(DWGS) < 2, reason="견본 부족")
def test_폴더_일괄과_jobs(tmp_path):
    r = run("convert", str(SAMPLES), "-o", str(tmp_path), "--jobs", "3")
    j = json.loads(r.stdout)
    assert j["total"] == len(DWGS)
    assert j["succeeded"] >= len(DWGS) - 1
