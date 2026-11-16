"""DXF 검증: ezdxf로 열어 구조 요약을 낸다(선택 의존)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

# $INSUNITS 코드 -> 이름(일부)
UNITS = {0: "단위 없음", 1: "인치", 2: "피트", 4: "밀리미터", 5: "센티미터", 6: "미터", 7: "킬로미터"}


def ezdxf_available() -> bool:
    try:
        import ezdxf  # noqa: F401
        return True
    except ImportError:
        return False


def verify_dxf(path: Path) -> dict:
    """열기 성공 여부와 레이어/엔티티/블록/단위/범위 요약. ezdxf 필요."""
    import ezdxf
    from ezdxf import bbox, recover

    res = {"file": str(path), "ok": False, "error": None}
    try:
        try:
            doc = ezdxf.readfile(str(path))
            res["recovered"] = False
        except (ezdxf.DXFStructureError, UnicodeDecodeError):
            # 엄격 읽기 실패 시 복구 모드로 한 번 더(LibreDWG 출력의 사소한 결함 대비)
            doc, _auditor = recover.readfile(str(path))
            res["recovered"] = True
        msp = doc.modelspace()
        cnt = Counter(e.dxftype() for e in msp)
        units = doc.header.get("$INSUNITS", 0)
        ext = None
        try:
            box = bbox.extents(msp, fast=True)
            if box.has_data:
                ext = {"min": [round(v, 6) for v in box.extmin], "max": [round(v, 6) for v in box.extmax]}
        except Exception as e:
            ext = {"error": f"{type(e).__name__}: {e}"}
        res.update({
            "ok": True,
            "dxf_version": doc.dxfversion,
            "layers": len(doc.layers),
            "entities_total": sum(cnt.values()),
            "entities": dict(cnt.most_common()),
            "blocks": len([b for b in doc.blocks if not b.name.startswith("*")]),
            "units": {"code": units, "name": UNITS.get(units, "기타")},
            "extents": ext,
        })
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
    return res
