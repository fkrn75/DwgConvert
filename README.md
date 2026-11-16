# DwgConvert

DWG 파일을 DXF로 바꾸는 독립 명령줄 도구입니다. 실제 변환은 GPL-3.0 라이브러리 [LibreDWG](https://www.gnu.org/software/libredwg/)의 `dwg2dxf` 실행 파일이 하고, 이 프로그램은 그것을 하위 프로세스로 불러 결과를 JSON으로 보고합니다.

## 라이선스와 경계

- 이 프로그램은 **GPL-3.0-or-later** 입니다(`LICENSE` 참고). LibreDWG가 GPL-3.0(또는 그 이후 버전)이기 때문입니다.
- LibreDWG: Copyright (C) Free Software Foundation, Inc. 및 LibreDWG 기여자. GNU 프로젝트이며 GPL-3.0-or-later 로 배포됩니다. 이 저장소에는 LibreDWG 바이너리를 넣지 않고, 공식 릴리스를 받는 스크립트만 둡니다.
- **외부 도구(예: BIM 엔진)는 이 프로그램을 별도 프로세스로만 호출해야 합니다.** 명령줄 인자와 JSON, 그리고 파일(DXF)만으로 통신하고, 이 저장소의 코드를 import하거나 링크하지 않습니다. 이렇게 하면 GPL 코드가 호출하는 쪽 프로그램으로 번지지 않습니다.

## 설치

Python 3.10 이상이 필요합니다. 표준 라이브러리만으로 변환이 되고, `verify`만 `ezdxf`(MIT)가 필요합니다.

```
py -3 -m venv .venv
.venv\Scripts\python -m pip install ezdxf pytest
.venv\Scripts\python tools\fetch_libredwg.py     # LibreDWG 0.14 win64 를 vendor\libredwg 에 받고 sha256 대조
```

LibreDWG를 찾는 순서: `--libredwg-dir` → 환경변수 `LIBREDWG_DIR` → `vendor/libredwg` → PATH.

## 사용법

```
python -m dwgconv doctor
python -m dwgconv convert 도면.dwg -o 출력폴더
python -m dwgconv convert 도면폴더 -o 출력폴더 --jobs 4 --timeout 600 --overwrite
python -m dwgconv convert 도면.dwg -o 출력폴더 --dxf-version r2000
python -m dwgconv verify 출력폴더\도면.dxf
```

- 폴더를 주면 하위 폴더의 `.dwg`를 모두 찾아 같은 하위 구조로 출력합니다.
- `--dxf-version`: `r12 r14 r2000 r2004 r2007 r2010 r2013 r2018`.
- 한글 경로: `dwg2dxf`가 윈도에서 한글 경로를 못 다루므로, 파일마다 영문 임시 폴더에 복사해 변환한 뒤 결과를 옮깁니다. 입력 파일은 읽기만 합니다.

## 출력 JSON

`convert`는 표준출력에 JSON 한 개를 냅니다.

```json
{
  "libredwg": "dwg2dxf 0.14",
  "total": 1, "succeeded": 1, "failed": 0,
  "files": [{
    "input": "...", "output": "...", "ok": true, "error": null,
    "dwg_version": "2018", "input_bytes": 19848, "output_bytes": 12345,
    "sha256": "...", "seconds": 0.03,
    "libredwg": {"exit_code": 0, "lines": 14, "warnings": 14, "errors": 0, "samples": ["..."]}
  }]
}
```

`verify`는 `ok`, `dxf_version`, `layers`, `entities_total`, `entities`(종류별 개수), `blocks`, `units`, `extents`를 냅니다. `doctor`는 LibreDWG 위치·버전과 ezdxf 유무를 냅니다.

## 종료 코드

| 코드 | 뜻 |
|---|---|
| 0 | 전부 성공 |
| 1 | 일부(또는 전부) 파일 실패 |
| 2 | 사용법 오류, 입력 없음 |
| 3 | LibreDWG 없음(`verify`는 ezdxf 없음) |

## 시험

```
.venv\Scripts\python tools\fetch_samples.py      # LibreDWG 시험 견본을 samples\ 에 받음(커밋 안 됨)
.venv\Scripts\python -m pytest
```

견본이나 LibreDWG가 없으면 해당 시험은 건너뜁니다.

## 한계

- LibreDWG 0.14가 읽지 못하는 DWG 버전·객체는 변환이 실패하거나 일부 객체가 빠집니다. 새 버전(2018 이후)이나 일부 프록시/사용자 정의 객체, 3D 솔리드(ACIS) 등은 불완전할 수 있습니다.
- LibreDWG는 많은 경고를 stderr에 냅니다. 종료 코드가 0이어도 `libredwg.warnings`/`errors`가 크면 결과를 `verify`로 확인하세요.
- DXF 버전을 낮추면 새 객체가 사라질 수 있습니다.
- LibreDWG 릴리스의 `.sig` 서명은 공개키가 없어 검증하지 못했고, 대신 zip의 sha256을 코드에 고정해 대조합니다.
