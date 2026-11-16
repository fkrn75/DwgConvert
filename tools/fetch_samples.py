"""시험용 DWG 견본을 samples/ 에 받는다(저장소에는 커밋하지 않음).

LibreDWG 저장소 test/test-data 의 작은 파일 중 버전별 대표를 받는다.
"""
import json
import sys
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/LibreDWG/libredwg/contents/test/test-data/{path}?ref=0.14"
RAW = "https://raw.githubusercontent.com/LibreDWG/libredwg/0.14/test/test-data/{path}"
SAMPLES = Path(__file__).resolve().parent.parent / "samples"
# 버전별 폴더(빈 문자열 = 최상위). 큰 파일(200KB 초과)은 건너뛴다
DIRS = ["", "2000", "2004", "2007", "2010", "2013", "2018"]
MAX_BYTES = 200_000
PER_DIR = 2


def main() -> int:
    SAMPLES.mkdir(exist_ok=True)
    n = 0
    for d in DIRS:
        req = urllib.request.Request(API.format(path=d), headers={"User-Agent": "dwgconv"})
        try:
            items = json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print(f"목록 실패 {d!r}: {e}", file=sys.stderr)
            continue
        files = [i for i in items if i["type"] == "file" and i["name"].lower().endswith(".dwg")
                 and 0 < i["size"] <= MAX_BYTES]
        for it in sorted(files, key=lambda i: i["size"])[:PER_DIR]:
            out = SAMPLES / ((d + "_" if d else "") + it["name"])
            if not out.exists():
                urllib.request.urlretrieve(RAW.format(path=(d + "/" if d else "") + it["name"]), out)
            print("받음", out.name, it["size"])
            n += 1
    print(f"견본 {n}개")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
