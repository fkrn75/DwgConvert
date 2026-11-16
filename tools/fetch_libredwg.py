"""LibreDWG 0.14 win64 공식 릴리스를 vendor/libredwg 에 받는다(sha256 고정 대조)."""
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip"
SHA256 = "1ad7e15344d20b3426c3435b078d82fb84b35062815946b2cca9c5fc9810fea8"
ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor"


def main() -> int:
    VENDOR.mkdir(exist_ok=True)
    zpath = VENDOR / "libredwg-0.14-win64.zip"
    print(f"받는 중: {URL}")
    urllib.request.urlretrieve(URL, zpath)
    got = hashlib.sha256(zpath.read_bytes()).hexdigest()
    if got != SHA256:
        zpath.unlink()
        print(f"sha256 불일치\n  기대 {SHA256}\n  실제 {got}", file=sys.stderr)
        return 1
    dest = VENDOR / "libredwg"
    with zipfile.ZipFile(zpath) as z:
        z.extractall(dest)
    print(f"완료: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
