# 작업 일지 (Journal)

역시간순(최근 작업이 위로)으로 작업 사항을 기록합니다. 작업이 완료되면 이 문서에 기록을 추가하세요.

## [2026-09-10] 산악기상정보(mountain_weather) API 실사용 결함 수정
- **작업자**: Claude Sonnet 5 (Claude Code)
- **내용**:
  - "산악 날씨 api도 손봐" 요청에 따라 `client.travel.mountain_weather()`를
    data.go.kr 15084696 상세 페이지 첨부 기술문서
    (`03_산악기상정보_기술문서_v1.5(수정본).docx`)와 실제 라이브 호출로 재검토했다.
  - **핵심 결함**: 실제 `mountListSearch` 응답에는 좌표·고도·지역명 필드가 전혀
    없는데(기술문서 응답 필드 표로 확인), 기존 parser는 `xValue`/`yValue` 같은
    필드가 있다고 가정했다. 기존 단위 테스트도 그런 필드를 포함한 합성 payload로
    통과하고 있어서 실제로는 라이브 호출 시 좌표가 항상 `None`이었다는 사실이
    가려져 있었다.
  - 기술문서 부록의 "지점 상세 코드" 표(454개 관측지점의 지역명·산이름·지점번호·
    위도·경도·고도)를 스크립트로 파싱해 `src/krforest/_mountain_stations.py`
    (`MOUNTAIN_STATIONS`)로 만들었다. `parse_mountain_weather`가 `obs_id`로 이
    표를 조회해 `latitude`/`longitude`/`elevation`/`region_name`(신규 필드)을
    채운다. row에 좌표가 실제로 있으면 정적 표보다 우선한다.
  - 응답의 결측 sentinel이 문자열 `"-"`임을 확인했다(라이브 검증 시점 기준 513개
    관측소 전부가 모든 동적 필드에서 `"-"`를 반환 — 전역적 상태로 보이며 이
    라이브러리가 고칠 수 있는 문제는 아니다). 숫자 필드는 `float("-")`의
    `ValueError`로 이미 우연히 `None`이 됐지만, `wind_direction_10m_name`/
    `wind_direction_2m_name`(문자열 방위 필드)은 그대로 `"-"`가 남아 있어
    `_none_if_dash` 헬퍼로 고쳤다.
  - `localArea`/`obsid`/`tm`이 문서에 명시된 선택 파라미터인데도 카탈로그
    `optional_params`가 비어 있었다 — 채우고, `client.travel.mountain_weather()`
    에 `local_area`/`obs_id`/`observed_at` named kwarg를 추가했다(다른
    endpoint와 시그니처 관례 통일).
  - 개발계정 신청 가능 트래픽이 10,000회/일(청정넷의 1,000회/일과 다름)임을
    확인해 catalog notes에 기록했다. ADR-010 참조.
- **검증**: 실제 서비스키로 obs_id=1890(파주 팔일봉) 라이브 호출 → 위도
  37.78/경도 126.92/고도 242.0/서울특별시 인접 경기도로 정확히 채워짐 확인.
  `pytest -q` 58 passed / live 11 passed·2 xfailed, `ruff check .`,
  `mypy src/krforest` 통과.

## [2026-09-09] 국립산림과학원 20-API 카탈로그 검토 — 청정넷(AICAN) 안전 데이터 2건 추가
- **작업자**: Claude Sonnet 5 (Claude Code)
- **내용**:
  - 자매 프로젝트(`korea-cli`)가 추적하는 `산림청 국립산림과학원` 20개 API 카탈로그를
    검토했다. 각 data.go.kr 상세 페이지에 첨부된 `.docx` 활용가이드를 직접
    다운로드·파싱해 실제 request/response 필드와 신청 가능 트래픽(개발계정
    1,000회/일)을 확인했다.
  - `forest_dust_measurements`(15078005, 청정넷_측정데이터)와
    `forest_dust_stations`(15078013, 청정넷_운영현황 attribute query)를 safety
    endpoint로 추가했다. `ForestDustMeasurement`/`ForestDustStation` 모델과
    parser, `client.safety.dust_measurements()`/`dust_stations()`를 구현했다.
  - 나머지 16개(생물 표본·임업경제·도서관/연구 12건 + 청정넷 WMS/WFS GIS 레이어
    4건)는 기존 travel/safety 범위 밖으로 판단해 `docs/forest-api.md`
    Exclusions에 사유와 함께 기록했다. ADR-009 참조.
  - AICAN 계열 API가 `response.header/body`로 감싸지 않고 `resultCode`/`items`를
    JSON 최상위에 바로 반환하는 것을 라이브 호출로 확인해, `_http._normalize_payload`에
    flat envelope 지원을 추가했다. 같은 API가 `contentType=JSON`(대문자)만
    JSON으로 응답하고 소문자는 무시하는 것도 확인해 `ApiEndpoint.response_type_value`
    override 필드를 추가했다.
  - 라이브 검증 중 `parser.parse_datetime`이 구분자 없는 12자리 `yyyyMMddHHmm`
    문자열에서 `strptime("%Y%m%d%H%M%S")`가 자릿수를 잘못 역추적해 분(minute) 값을
    훼손하는 기존 버그를 발견해 수정했다(예: `"202511011530"` → 이전 `15:03`, 이제
    `15:30`). 숫자 전용 문자열은 길이(8/10/12/14)로 형식을 고정한다. 이 버그는
    `mountain_weather`/`wildfire_risk_forecast` 등 기존 endpoint에도 영향을
    미치고 있었다.
  - **적대적 리뷰(전문 리뷰어 서브에이전트 2명, 서로 독립적으로 다른 관점에서 진행)**:
    한 명은 정확성(필드 매핑, envelope edge case, `parse_datetime` 견고성)을, 다른
    한 명은 API 설계 일관성·`SKILL.md` 규칙 준수·문서 정합성을 검토했다. 두 리뷰
    모두 실제 코드를 읽고 `pytest`/`ruff`/`mypy`를 직접 실행해 검증했다. 리뷰가 낸
    항목 중 재현 가능한 주장(예: XML fallback이 조용히 데이터를 잃는다는 주장)은
    직접 라이브 호출·인터프리터로 재검증한 뒤 반영 여부를 결정했다 — 해당 주장은
    실제 vendor XML 루트 태그(`ResponseBaseDTO`)가 아니라 다른 endpoint의 root
    태그(`response`)를 가정한 것으로 확인되어 반영하지 않았다. 실제로 반영한
    수정:
    - `parse_datetime`이 `fromisoformat`도 우회하도록 재구성. 11/13/15자리처럼
      애매한 길이의 숫자열에서 `fromisoformat`이 구분자를 잘못 추정해 같은 종류의
      오류(예: `"20260820123"` → `23:00`)를 낼 수 있음을 리뷰가 지적해 검증 후
      수정 — 숫자 전용 입력은 이제 `fromisoformat`을 거치지 않는다.
    - `model_number` 필드가 pydantic `protected_namespaces=('model_',)` 기본값과
      충돌해 `pydantic>=2.7`(이 프로젝트가 허용하는 최소 버전)에서 import 시
      `UserWarning`을 낼 수 있음을 발견해 `equipment_reference_number`로 이름을
      바꿨다.
    - `obsrr_tpcd`가 관측소 분류가 아니라 사실상 고유 식별 코드(측정데이터·관측소
      속성 간 join key)로 기능함을 지적받아 `station_type_code`를 `station_code`로
      변경.
    - `obsrr_instl_dt`(날짜만 제공)를 `datetime`으로 만들면 timezone 변환 시
      날짜가 밀릴 수 있다는 지적에 따라 `installed_at`을 `str | None`으로 변경.
    - `address` 추출을 다른 parser 함수들과 일관되게 `_convert.extract_address`로
      변경.
    - live 테스트의 키 유출 검증이 `"serviceKey"`(소문자)를 확인해 실제로는
      `"ServiceKey"`(기본값)를 쓰는 이 두 endpoint에서 항상 통과하던 오류를
      수정(다른 lowercase override endpoint의 테스트를 잘못 복사한 것).
    - flat envelope의 에러(`resultCode="22"`→rate limit)·no-data(`"03"`)·미인식
      envelope(`ForestParseError`) 경로와, `mountain_weather`/
      `wildfire_risk_forecast`의 12자리 타임스탬프 회귀(비대칭 분(minute) 값)에
      대한 단위 테스트를 추가.
    - `catalog.py`의 새 entry 2건을 `API_ENDPOINTS` 튜플 끝(다른 wildfire entry와
      떨어져 있던 것을 정리)으로 옮겨 `docs/forest-api.md` 표 순서와 일치시킴.
    - ADR-009/`docs/resume.md`의 수치 불일치(측정데이터에 없는 `obsrr_group_cd`
      언급, "나머지 15개"→"12개", "생물표본 12건"→"생물표본·임업경제·도서관/연구
      12건") 정정.
- **검증**: 실제 서비스키로 `client.safety.dust_measurements()` 라이브 호출 성공
  (총 30,286,187건 확인), `dust_stations()`는 활용신청 미승인으로 auth xfail(기존
  패턴과 동일). 리뷰 반영 후 `pytest -q` 52 passed / live 11 passed, 2 xfailed,
  `ruff check .`, `mypy src/krforest` 통과.

## [2026-08-20] C05B~C05D 리뷰 반영 및 경계 보안 보강
- **작업자**: Codex
- **내용**:
  - `WildfireScope` Literal을 도입해 `mypy --strict` typed parser 오류를 제거했다.
  - V2 시군구 응답에서 `sigucode`/`sigun`을 우선해 지역 identity가 상위 시도 코드로
    잘못 잡히지 않게 했다.
  - Name-only SHP layer의 source ID hash에 geometry를 포함해 서로 다른 route가
    first-wins dedup으로 합쳐지지 않게 했다.
  - JSON/XML body-level 인증 오류의 메시지와 구조화 response에서 service key를
    재귀 redaction했다.
- **검증**: `pytest -q` 42 passed / live 11 skipped, `ruff check src tests`,
  `mypy --strict src/krforest` 통과.

## [2026-08-20] C05A 중첩 SHP 등산로 파서·source natural key 보강
- **작업자**: Codex
- **내용**:
  - `PBD0000041`의 지역별 중첩 ZIP 안 canonical SHP를 재귀 파싱하고, 동일 노선의
    `_geojson.zip`·`_gpx.zip` 형제 사본은 건너뛰도록 했다.
  - `ForestSpatialFeature.source_id`를 추가해 `PMNTN_SN`·`Name` 등 원천 식별자를
    `source_file`과 결합하고, 식별자가 없을 때만 raw/geometry SHA-1을 사용한다.
  - 산 이름·구간 이름을 결합한 표시명과 WGS84 route geometry를 보존한다.
  - CRS transformer 캐시로 수천 개 SHP layer의 반복 초기화 비용을 제거했다.
  - 실측 저메모리 census: 265,601,808 bytes / nested SHP ZIP 2,932개 / 원천 피처
    164,185개 / LineString 56,869개 / MultiLineString 191개. 동일 필드·geometry의
    완전 중복 3건은 parser에서 first-wins 제거한다.
  - route-only live parse는 Point를 제외하고 57,060개(LineString 56,869 /
    MultiLineString 191)를 반환했으며, 이름·geometry·source_id와 source_id 유일성을
    모두 확인했다.
- **검증**: 중첩 SHP 단위 테스트 2 passed, `ruff check .` 통과. 서비스키가 없는
  환경에서는 data.go.kr live API 테스트를 실행하지 않았고, 산림 파일 census는
  forest.go.kr에서 별도 완료했다.

## [2026-06-07] 로컬 저장 시 rustfs 동시 저장 및 전용 함수 추가
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `src/krforest/debug.py`의 `save_fixture` 함수 개선: 파일 저장 시 기존의 로컬 저장과 함께 `rustfs`에도 저장하도록 로직 추가.
  - 호환성 확보를 위해 내장 `open()` 함수 외에 `rustfs` 호출을 전담할 예비 함수 `save_to_rustfs`를 선언함.
  - 로컬 저장이 성공한 뒤 `rustfs` 저장 시도 중 발생한 예외는 무시하도록 처리하여 로컬 저장 안정성 유지.
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 기존 테스트 모두 통과.

## [2026-05-31] Windows Git 사용 원칙 명시 및 `.codegraph` gitignore 재고정
- **작업자**: Codex (AI Agent)
- **내용**:
  - `AGENTS.md`의 개발 환경 정책에 git 관련 명령은 Windows Git(`C:\Program Files\Git\cmd\git.exe`)를 사용한다는 원칙을 추가.
  - `SKILL.md`의 로컬 환경 반복 이슈에 WSL `git`이 worktree의 Windows 경로 `.git`를 오해해 실패할 수 있다는 배경과 함께 동일 원칙을 추가.
  - `.gitignore`의 CodeGraph ignore 패턴을 `.codegraph`로 명시해 디렉터리 이름 자체가 무시되도록 재고정.
  - `docs/resume.md`를 현재 상태에 맞게 갱신하고 다음 작업에 PR/머지 항목을 반영.
- **결과**: 에이전트가 이 worktree에서 git 명령을 실행할 때 Windows Git 사용 기준이 문서화되었고, `.codegraph`는 ignore 대상임을 명확히 유지.

## [2026-05-27] `python-kraddr-base` 의존성 완전 제거 및 좌표·주소 평탄화
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `pyproject.toml`의 `dependencies`에서 `python-kraddr-base>=0.1.5` 항목 제거. `tool.mypy.mypy_path`도 함께 제거.
  - `src/krforest/_convert.py`에 `extract_coordinate(row)` / `extract_address(row)` 헬퍼와 결측 sentinel 처리(-99, -999, 0) 추가.
  - `models.py`의 좌표·주소 필드를 다음과 같이 평탄화:
    - `coordinate: PlaceCoordinate | None` → `latitude: float | None`, `longitude: float | None`
    - `address: Address | None` → `address: str | None`
  - `parser.py`, `processor.py`, `spatial.py`가 더 이상 `kraddr.base`를 import하지 않도록 재작성. `spatial._place_coordinate`/`_shape_centroid`/`_geometry_centroid`는 `(lat, lon)` 튜플 반환으로 변경.
  - `__init__.py`의 `Address`/`PlaceCoordinate` 재노출 제거. `__version__`을 `0.2.0`으로 올림(파괴적 변경).
  - `tests/test_client.py`, `tests/test_live.py`에서 외부 클래스 import 및 `.coordinate`/`.address.display_address` 단언을 새 평탄 필드 기준으로 갱신.
  - `README.md`, `SKILL.md`, `docs/forest-api.md`, `docs/decisions.md`에서 `kraddr.base` 언급 제거 및 새 모델 인터페이스 반영.
  - `docs/decisions.md`에 ADR-008 추가 (`python-kraddr-base` 의존 제거 및 좌표·주소 평탄화 결정).
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 외부 도메인 패키지 의존 없이 동작.

## [2026-05-24] 코드 리뷰 반영 및 문서 체계 확장
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `src/krforest` 전체 코드 리뷰 수행. 다음 사항 반영:
    - `spatial._member_by_suffix` 죽은 helper 제거.
    - `config.py` 모듈 함수 사이 공백 보정.
    - `client._page`의 `pageNo`/`numOfRows` 폴백을 가독성 좋게 재작성.
    - `client.recreation_forest_reservations`에서 endpoint 카탈로그가 이미 정의한 `response_format="xml"` 인자를 제거(중복).
    - `_forest_go_request_with_retry`에 지수 백오프(0.5 * 2^attempt) 추가 — 무지연 3연속 재시도를 회피.
    - `models.CallContext.provider`/`CatalogEntry.provider`에서 `Provider | str` 중복을 `str`로 단순화.
  - `SKILL.md`/`docs/decisions.md`/`AGENTS.md`/`docs/resume.md`/`docs/journal.md`/`docs/tasks.md` 갱신.
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 회귀 없음.

## [2026-05-24] 문서화 전략 개편 진입
- **작업자**: Antigravity (AI Agent)
- **내용**: `python-kraddr-geo`를 참조하여 `SKILL.md`, `resume.md`, `tasks.md`, `decisions.md` 등 문서 체계 도입. `AGENTS.md`를 진입점으로 축소.
- **결과**: PR 브랜치(`docs/methodology-and-refactor`) 생성 및 기반 작업 완료.
