# DECISIONS — Architecture Decision Records

본 문서는 `python-krforest-api` 프로젝트의 의사결정을 시간순으로 누적한다. 결정이 뒤집힐 때도 이전 기록은 지우지 않고 `superseded by ADR-XXX`로 표시한다.

## ADR 표준 형식

```
## ADR-NNN: <결정 요약>

- 상태: proposed | accepted | superseded by ADR-XXX
- 날짜: YYYY-MM-DD
- 결정자: <agent | human>

### 컨텍스트
<무엇이 문제였나. 어떤 제약·요구가 있었나.>

### 결정
<무엇을 정했는가. 한 문장으로.>

### 근거
-

### 결과(긍정)
-

### 결과(부정)
-

### 후속
- (open) 추가 검증 필요한 사항
```

---

## ADR-001: 에이전트 문서화 전략(Methodology) 도입

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human + agent

### 컨텍스트
에이전트가 코드를 관리하고 유지보수할 때 컨텍스트 유지와 일관성 확보가 필요했다. 기존 `AGENTS.md`는 항목이 너무 많아 진입점 역할을 못 했다.

### 결정
`python-kraddr-geo`의 문서화 구조를 차용하여, 에이전트 가이드(`SKILL.md`), 현재 상태 기록(`resume.md`), 일지(`journal.md`), 백로그(`tasks.md`), 의사결정(`decisions.md`)으로 분리한다.

### 근거
- 진입점(`AGENTS.md`)과 상세 규칙(`SKILL.md`)을 분리하면 새 에이전트가 첫 화면에서 압도되지 않는다.
- 작업 후 갱신 대상(journal/resume/decisions)을 명시해 컨텍스트 유실을 막을 수 있다.
- `kraddr-geo`에서 같은 구조가 이미 동작 검증됨.

### 결과(긍정)
- 새 작업 진입 비용 감소.
- 의사결정 근거가 누적되어 같은 논의를 다시 하지 않는다.

### 결과(부정)
- 작업 완료 시 문서 갱신 의무가 추가된다.

---

## ADR-002: 서비스 키는 `DATA_GO_KR_SERVICE_KEY` 단일 환경변수만 사용한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
초기 구현은 `KRFOREST_SERVICE_KEY` 등 별칭 환경변수를 fallback으로 허용했다. 키가 여러 곳에 흩어지면 어떤 키가 실제로 쓰였는지 추적이 어렵고, 유출 시 회수 범위가 모호해진다.

### 결정
키 로드는 `config.from_env`가 `DATA_GO_KR_SERVICE_KEY` **하나만** 읽도록 고정한다. 새 별칭은 도입하지 않는다.

### 근거
- 동일 키가 `data.go.kr` 게이트웨이와 `forest.go.kr` OpenAPI 모두에서 통과한다(live test로 확인).
- 키 마스킹/감사를 단순화한다.
- 같은 계열 라이브러리(`pykma`, `pykex`)의 키 관리 정책과 일관.

### 결과(긍정)
- 코드 경로 단일화, 키 유출 시 회수 표면 최소화.
- 테스트 fixture와 live test가 같은 환경변수를 공유.

### 결과(부정)
- 외부에서 다른 이름의 환경변수를 쓰던 사용자는 마이그레이션이 필요.

---

## ADR-003: 응답 envelope의 body-level `resultCode`를 반드시 검증한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: agent

### 컨텍스트
data.go.kr 게이트웨이는 인증 실패, 쿼터 초과, 활용신청 미승인 같은 오류를 HTTP 200으로 반환하면서 body의 `response.header.resultCode`(또는 `OpenAPI_ServiceResponse.cmmMsgHeader.returnReasonCode`)에 코드를 담는다. HTTP 상태만 보면 오류를 놓친다.

### 결정
`_http._normalize_payload`와 `_http._raise_openapi_service_error`에서 정상 코드(`""`, `"00"`, `"0000"`, `"NORMAL_CODE"`)만 통과시키고, `"03"`(no data)은 빈 `Page`로 정상 처리한다. 나머지는 `failure_kind`가 부여된 `ForestApiError` 하위로 매핑한다.

### 근거
- 인증 오류와 데이터 없음을 명확히 구분해야 호출자가 재시도 정책을 정할 수 있다.
- envelope 차이는 상위 코드에서 신경 쓰지 않도록 transport 레이어에서 흡수.

### 결과(긍정)
- 호출자는 `ForestAuthError`/`ForestRateLimitError`/`ForestNoDataError`로 분기하면 된다.
- live test가 인증 미승인을 `xfail`로 분류 가능.

### 결과(부정)
- 새 코드값을 만날 때마다 매핑을 보완해야 한다.

---

## ADR-004: 얇은 래퍼 대신 검증된 자매 라이브러리 구조를 그대로 가져온다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
공공데이터 클라이언트는 패턴이 비슷하다(`ServiceKey`, `pageNo`, `numOfRows`, XML/JSON envelope). 새 wrapper/adapter/gateway 레이어를 만들면 호출 경로만 늘고 유지보수 비용이 커진다.

### 결정
`pykma`, `pyopinet`, `pykex` 등 자매 라이브러리에 검증된 구현 패턴이 있으면 구조와 동작을 그대로 가져와 맞춘다. 장기 호환 alias나 임시 facade는 만들지 않는다.

### 근거
- 검증된 패턴 재사용은 버그 표면을 줄인다.
- 사용자(다른 클라이언트도 함께 쓰는 개발자)에게 일관된 API 표면 제공.

### 결과(긍정)
- `ForestClient(api_key=..., timeout=..., max_rps=...)` 형태와 namespace 패턴이 자매 라이브러리와 동일.

### 결과(부정)
- 자매 라이브러리의 결함도 함께 가져올 수 있어, 한쪽 수정 시 다른 쪽도 점검해야 한다.

---

## ADR-005: 라이브러리 API는 async-only로 둔다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
공공데이터 호출은 페이지네이션·다중 dataset 결합·rate limit 동시 제어가 잦다. 동기/비동기를 모두 제공하면 코드 경로가 두 배가 되고 mypy strict 통과가 어려워진다.

### 결정
`ForestClient`는 async-only다. 동기 컨텍스트(Jupyter, 단순 스크립트)에서는 호출자가 `asyncio.run`으로 감싼다.

### 근거
- `httpx.AsyncClient`와 자연스럽게 결합.
- `_ratelimit.AsyncTokenBucket`으로 동시성·RPS 제어 단순.
- `pytest-asyncio`로 테스트 일원화.

### 결과(긍정)
- 코드 경로 단순화, mypy strict 통과 용이.
- 페이지 순회(`iter_pages`)와 다중 파일데이터 결합 시 동시성 제어가 자연스러움.

### 결과(부정)
- 단순 동기 환경에서는 한 줄 래퍼가 필요.

---

## ADR-006: 레코드 변환의 책임을 parser / processor / spatial로 분리한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: agent

### 컨텍스트
공공데이터는 단일 row → 모델 변환, 여러 CSV/Excel join → 단일 객체 생성, SHP/GeoJSON/GPX → 공간 DTO 변환 등 변환 유형이 서로 다르다. 한 파일에 모두 두면 모듈 책임이 빠르게 무너진다.

### 결정
- `parser.py`: **단일 row → 공개 모델** (예: `parse_mountain_weather`).
- `processor.py`: **여러 파일·여러 row를 join해 단일 객체 생성** (예: `build_recreation_forests`).
- `spatial.py`: **SHP/GeoJSON/GPX → 좌표·도형 DTO** (예: `forest_spatial_points`).

### 근거
- 호출 위치만 봐도 책임이 짐작된다.
- 테스트 fixture가 모듈 단위로 분리되어 회귀가 명확.

### 결과(긍정)
- 새 변환 추가 시 어느 파일에 넣을지 즉시 결정 가능.

### 결과(부정)
- 세 모듈이 모두 같은 row key 셋(`_INSTITUTION_ID_KEYS` 등)을 참조해야 할 때 중복이 생긴다.

---

## ADR-007: data.go.kr 파일데이터는 JSON-LD `contentUrl`을 우선 사용한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
data.go.kr 파일 상세 페이지는 다운로드 URL을 HTML/JS로 동적 구성한다. URL을 하드코드하면 사이트 개편 시 한꺼번에 깨진다.

### 결정
파일데이터 다운로드 URL은 상세 페이지의 JSON-LD(`type=application/ld+json`) 안의 `contentUrl`을 우선 탐색하고, 폴백으로 `"contentUrl": "..."` 정규식을 사용한다. forest.go.kr는 별도 popup → history → ZIP 흐름을 유지한다.

### 근거
- JSON-LD는 검색엔진·메타데이터 표준이라 페이지 개편 시에도 비교적 안정.
- 폴백 정규식으로 JSON-LD가 일시 누락된 경우에도 동작.

### 결과(긍정)
- data.go.kr 페이지 구조 변경 영향이 줄어듦.

### 결과(부정)
- forest.go.kr는 별도 흐름이라 두 가지 경로를 모두 유지해야 한다.

---

## ADR-008: `python-kraddr-base` 의존성 제거 및 좌표·주소 평탄화

- 상태: accepted
- 날짜: 2026-05-27
- 결정자: human

### 컨텍스트
공공데이터 응답에서 좌표·주소를 노출하기 위해 외부 도메인 패키지 `python-kraddr-base`의 `Address`와 `PlaceCoordinate`를 직접 import해 사용해 왔다. 그러나 이 의존은 (1) 설치 시점 추가 패키지가 필요하고 (2) mypy `mypy_path`에 외부 소스 경로를 끼워 넣어야 하며 (3) 산림청·data.go.kr 데이터에는 `Address`의 상세 필드(우편번호, 행정코드 등) 대부분이 의미 없는 경우가 많았다. ADR-004(얇은 래퍼 금지)에 따른 단순화 원칙과도 충돌이 있었다.

### 결정
`python-kraddr-base` 의존을 완전히 제거하고, 좌표·주소를 모델에 평탄한 원시 타입으로 노출한다.

- 좌표: `latitude: float | None`, `longitude: float | None`
- 주소: `address: str | None`

응답 row에서 위 값을 뽑는 책임은 `krforest._convert.extract_coordinate(row)`와 `krforest._convert.extract_address(row)`가 담당한다.

### 근거
- 패키지 설치·배포 의존을 1단계 줄인다.
- mypy strict 환경에서 외부 경로(`mypy_path`) 설정을 없앤다.
- 산림청·data.go.kr 응답의 좌표·주소는 raw row에 그대로 보존되어 있어, 원시 필드로도 충분히 활용 가능하다.
- 호환성 부담을 의도적으로 끊어, 외부 사용자가 새 필드명(`latitude`/`longitude`/`address`)에 맞춰 마이그레이션하도록 함.

### 결과(긍정)
- 라이브러리가 `httpx`, `pydantic`, `pyproj`, `pyshp` 4개 의존만으로 동작.
- 사용자 코드가 외부 도메인 클래스를 import할 필요 없음.
- 좌표 결측 sentinel(-99, -999, 0)을 `_convert.extract_coordinate`가 일관되게 처리.

### 결과(부정)
- 기존 API(`item.coordinate`, `item.address.display_address`)를 쓰던 사용자는 코드 변경이 필요(파괴적 변경).
- 주소의 도로명/지번 분리 같은 추가 정보가 필요한 사용자는 직접 raw row에서 파싱해야 함.

### 후속
- (open) 사용자 가시 변경 → `__version__`을 `0.2.0`으로 올리고 README/SKILL/문서 모두 새 필드명에 맞춰 갱신.

---

## ADR-009: 국립산림과학원 20-API 카탈로그 검토 — 청정넷(AICAN) 안전 데이터 2건 추가, 나머지 16건 제외

- 상태: accepted
- 날짜: 2026-09-09
- 결정자: human + agent

### 컨텍스트
자매 프로젝트(`korea-cli`)의 API 커버리지 카탈로그가 `산림청 국립산림과학원` 산하
20개 data.go.kr dataset을 모두 "외부 링크"(미구현)로 표시했다. 사용자가 이 20건을
검토해 빠진 부분을 구현하라고 요청했으나, 대부분은 `SKILL.md`/`docs/forest-api.md`가
이미 명시한 범위 제외 기준(생물 표본, 임업경제, 도서관/연구, 법령)에 정확히
해당했다. 사용자에게 확인한 결과 "여행/안전에 맞는 것만 추가하고 나머지는 제외 사유를
문서화"하는 방향으로 결정했다.

### 결정
20건 중 산악기상(`mountain_weather`, 기구현)과 산불위험예보(`wildfire_risk_forecast*`,
기구현)를 제외한 나머지를 검토해, 청정넷(AICAN) 산림 미세먼지 실측 API 2건만 추가한다.

- `forest_dust_measurements`(15078005, `AicanDustData/dustData`): 관측소별
  PM10·PM2.5·PM1.0과 온도·습도·풍향·풍속 10분 단위 실측값. 외출/등산 전 대기질을
  확인할 수 있어 safety로 분류한다.
- `forest_dust_stations`(15078013, `AicanObsrrInfo/obsrrInfo`): 관측소 명칭,
  좌표, 주소, 설치일, 장비 정보. 측정데이터의 `obsrr_tpcd`(`station_code`)를
  해석하려면 필요한 동반 데이터라 함께 추가한다(`ForestDustMeasurement.station_code`
  와 `ForestDustStation.station_code`가 join key다. `obsrr_group_cd`는 관측소
  속성에만 있고 측정데이터에는 없다). 같은 API의 WMS/WFS 지도 조회 기능
  (`obsrrInfoWms`, `obsrrInfoWFS`)은 이미지/GML 응답이라 구현하지 않는다.

나머지 16건(생물표본·임업경제·도서관/연구 12건 + 청정넷 GIS 레이어 4건: 그린인프라·
그레이인프라·사용자가치·유관기관변환자료)은 `docs/forest-api.md`의 `Exclusions`
절에 사유와 함께 기록하고 구현하지 않는다. 청정넷 GIS 레이어 4건은 홍릉·고매·시화·
양재·관악·제주 등 소수 연구 대상지에 한정된 정적 WMS/WFS 분류 레이어라 여행자에게
실행 가능한 정보를 주지 않는다.

### 근거
- `SKILL.md` 1절이 이미 "생물 표본, 임업경제, 법령해석, 사업자 등록, 행정 통계 데이터는
  의도적으로 범위에서 제외"를 명시하고 있어, 이번 검토는 새 원칙이 아니라 기존 원칙의
  적용이다.
- 각 API의 data.go.kr 상세 페이지 첨부 활용가이드(`.docx`)를 직접 다운로드해 실제
  request/response 필드, 에러 코드, 신청 가능 트래픽(개발계정 1,000회/일)을
  확인했다. 카탈로그 요약만으로는 실제 스펙(특히 `contentType` 대소문자 구분, flat
  envelope)을 알 수 없었다.
- 실제 서비스키로 `forest_dust_measurements`를 라이브 호출해 확인했다: 이 API 계열은
  `response.header/body`로 감싸지 않고 `resultCode`/`items`를 JSON 최상위에 바로
  반환하며, `contentType=json`(소문자)은 무시되고 XML로 응답한다(대문자 `JSON`만
  유효). 이 두 가지는 기존 `_http._normalize_payload`와 `ApiEndpoint`가 다루지 못해
  인프라를 확장해야 했다.

### 결과(긍정)
- `_http._normalize_payload`가 `response.header/body` 중첩 envelope와
  `resultCode`가 최상위에 바로 오는 flat envelope를 모두 지원하게 됐다. 향후
  다른 산림청 API가 같은 flat 패턴을 쓰더라도 재사용 가능하다.
- `ApiEndpoint.response_type_value`(및 `CatalogEntry` 동일 필드)를 추가해,
  응답 타입 파라미터 값이 소문자 `"json"`이 아닌 provider별 override(예:
  `"JSON"`)를 catalog 선언만으로 표현할 수 있다.
- 라이브 검증 과정에서 `parser.parse_datetime`이 구분자 없는 12자리
  `yyyyMMddHHmm` 문자열을 `%Y%m%d%H%M%S`로 잘못 역추적해 분(minute) 값을
  훼손하던 기존 버그(예: `"202511011530"` → `15:03`)를 발견해 함께 고쳤다. 이
  버그는 `mountain_weather`/`wildfire_risk_forecast` 등 기존 12자리 타임스탬프
  필드에도 영향을 미치고 있었다. 숫자 전용 문자열은 이제 `fromisoformat`을 거치지
  않고 길이(8/10/12/14)로만 형식을 고정한다 — `fromisoformat`도 11/13/15자리처럼
  애매한 길이의 숫자열에서 구분자를 잘못 추정해 같은 종류의 오류를 낼 수 있어,
  숫자 전용 입력은 처음부터 그 경로를 타지 않게 했다.
- 전문 리뷰어 2명의 독립적 적대적 리뷰에서 나온 교정: `model_number` 필드명이
  pydantic 2.7–2.9의 `protected_namespaces=('model_',)` 기본값과 충돌해
  import 시 `UserWarning`을 낼 수 있어(이 프로젝트는 `pydantic>=2.7`을 허용) 필드를
  삭제 전 `equipment_reference_number`로 변경했다. `obsrr_tpcd`는 관측소별
  분류가 아니라 사실상 고유 식별 코드(측정데이터·관측소 속성 간 join key)로
  기능해 `station_type_code`가 아닌 `station_code`로 이름을 바꿨다. `obsrr_instl_dt`
  는 vendor가 날짜(yyyyMMdd)까지만 제공해 `installed_at`을 datetime이 아닌
  원본 문자열로 노출한다(datetime으로 만들면 timezone 변환 시 날짜가 밀릴 수
  있다). `address`는 `parser.py`의 다른 함수들과 일관되게 `_convert.extract_address`
  로 추출하도록 바꿨다.

### 결과(부정)
- catalog와 문서에 "구현하지 않는 이유"를 명시적으로 남겨야 해서 `forest-api.md`가
  길어졌다. 다만 향후 같은 조사를 반복하지 않게 해준다.
- `response_type_value` 필드 추가로 `ApiEndpoint`/`CatalogEntry`의 필드 수가
  늘었다(ADR-004의 "얇은 래퍼 금지" 정신과는 별개로, 이는 provider 스펙 차이를
  흡수하는 필수 필드라 판단했다).

### 후속
- (open) 청정넷 GIS 레이어(WMS/WFS)나 나머지 16건 중 하나라도 향후 travel/safety
  use case가 생기면 이 ADR과 `forest-api.md` Exclusions 표를 갱신한 뒤 재검토한다.

---

## ADR-010: `mountain_weather`는 좌표·고도를 정적 참조 테이블에서 채운다

- 상태: accepted
- 날짜: 2026-09-10
- 결정자: human + agent

### 컨텍스트
"산악 날씨 api도 손봐"라는 요청에 따라 `client.travel.mountain_weather()`를
ADR-009와 같은 방식(data.go.kr 상세 페이지 첨부 `.docx` 기술문서를 직접
다운로드해 실제 스펙 확인 + 라이브 호출 검증)으로 재검토했다.

기존 구현은 `parse_mountain_weather`가 `_convert.extract_coordinate(row)`로
매 row에서 `xValue`/`yValue` 등의 좌표 필드를 찾도록 되어 있었고, 기존
단위 테스트(`test_mountain_weather_returns_place_coordinate`)도 그런 필드가
있다고 가정한 합성(fabricated) payload로 통과했다. 그러나 실제 서비스키로
`mountListSearch`를 라이브 호출한 결과와, 첨부 기술문서
(`03_산악기상정보_기술문서_v1.5(수정본).docx`)의 응답 필드 표를 대조한 결과,
**이 API는 좌표·고도·지역명 필드를 단 하나도 반환하지 않는다**는 것을 확인했다.
즉 이전까지 `client.travel.mountain_weather()`가 실제 서비스키로 호출될 때는
`latitude`/`longitude`가 항상 `None`이었다 — 테스트만 통과하고 있었을 뿐, 실제로
동작하지 않던 기능이다.

같은 기술문서 부록("지점 상세 코드")에 454개 관측지점 전체의 지역명·산이름·
지점번호·위도·경도·고도가 정적 표로 실려 있었다. 이 표가 좌표를 얻을 수 있는
유일한 출처다.

라이브 검증 중 추가로 확인한 것:
- 응답의 모든 동적 필드(기온·습도·풍향·풍속·강수량·관측시간)는 결측을 문자열
  `"-"`로 표현한다. 검증 시점 기준 513개 관측소 전부가 모든 필드에서 `"-"`를
  반환했다(관측소 개별 장애가 아니라 전역적인 상태로 보인다 — 이 라이브러리가
  고칠 수 있는 문제는 아니다). 숫자 필드는 `to_float_or_none`이 `float("-")`의
  `ValueError`를 잡아 이미 우연히 `None`이 되고 있었지만, 문자열 필드
  (`wd10mstr`/`wd2mstr`, 풍향 방위 문자)는 그대로 `"-"`가 남아 있었다.
- `localArea`(지역코드), `obsid`(지점번호), `tm`(정확한 관측시간)이 문서에
  명시된 선택 파라미터였는데도 `catalog.py`의 `optional_params`가 비어 있었고
  `client.travel.mountain_weather()`에도 named kwarg가 없었다(`**params`로
  전달은 가능했지만 카탈로그/시그니처 어디에도 드러나지 않았다).
- 신청 가능 트래픽은 개발계정 10,000회/일로, 청정넷(AICAN) 계열의 1,000회/일과
  다르다(엔드포인트마다 다르므로 매번 확인해야 한다).

### 결정
1. 첨부 기술문서의 "지점 상세 코드" 표를 그대로 옮긴 정적 참조 모듈
   `src/krforest/_mountain_stations.py`(`MOUNTAIN_STATIONS: dict[str, MountainStationRef]`,
   454개 지점번호 키)를 추가한다. 문서 텍스트에서 수기 필사 대신 스크립트로
   테이블을 파싱·생성해 오타를 방지했다.
2. `parse_mountain_weather`가 `obs_id`로 이 표를 조회해 `latitude`/`longitude`/
   `elevation`/`region_name`(신규 모델 필드)을 채운다. 응답 row에 좌표 필드가
   실제로 있으면(향후 provider 변경 등) 정적 표보다 그 값을 우선한다. 표에 없는
   `obs_id`는 조용히 `None`으로 남긴다(예외를 던지지 않는다).
3. 결측 문자열 `"-"`를 명시적으로 걸러내는 `_none_if_dash` 헬퍼를 추가해
   `wind_direction_10m_name`/`wind_direction_2m_name`에 적용한다.
4. `catalog.py`의 `mountain_weather` `optional_params`에 `localArea`/`obsid`/
   `tm`을 채우고, `client.travel.mountain_weather()`에 `local_area`/`obs_id`/
   `observed_at` named kwarg를 추가해 다른 endpoint(`wildfire_stats` 등)와
   시그니처 관례를 맞춘다.

### 근거
- 실제로 동작하지 않는 기능(항상 `None`인 좌표)을 "동작한다"고 문서·테스트가
  주장하는 상태를 그대로 둘 수 없었다.
- 정적 표는 벤더가 새 관측소를 등록할 때만 바뀌는 저빈도 참조 데이터라, 매
  호출마다 별도 API를 부르는 대신 라이브러리에 내장하는 것이 ADR-004(얇은 래퍼
  금지, 검증된 패턴 재사용)와 어긋나지 않는다 — 오히려 provider가 제공하지
  않는 정보를 provider의 공식 문서에서 그대로 가져온 것이다.
- `"-"` 결측 처리는 숫자 필드에서 이미 우연히 맞았던 동작을 문자열 필드에도
  동일하게 명시적으로 적용해 일관성을 맞춘 것뿐이며, 새로운 정책을 도입한 것은
  아니다.
- **`parser.py` vs `processor.py` 경계(SKILL.md 규칙 12).** `obs_id` 기준
  정적 표 조회는 ADR-006이 `parser.py`의 책임으로 정의한 "단일 remote row →
  공개 모델" 변환의 일부로 본다 — 두 번째 row나 별도 다운로드 파일을 join하지
  않고, in-package 상수를 참조할 뿐이기 때문이다. ADR-006이 실제로
  `parse_mountain_weather`를 `parser.py` 예시로 들고 있기도 하다. 반대로
  `processor.py`는 "여러 **파일**·여러 row를 join"하는 경우(휴양림 CSV 4개
  join 등)를 위한 것이라 이 조회에는 맞지 않는다. `client.py::_page()`가
  `parser: Callable[[dict], T]` 시그니처(단일 row 입력)로 고정돼 있어,
  `processor.py`로 옮기면 파이프라인에 불필요한 단계가 하나 더 생긴다.

### 결과(긍정)
- `client.travel.mountain_weather()`가 실제 서비스키로도 `latitude`/
  `longitude`/`elevation`/`region_name`을 채운 레코드를 반환한다(라이브
  검증: obs_id=1890 → 위도 37.78/경도 126.92/고도 242.0/서울특별시 인접
  경기도, 문서 표 값과 일치).
- 알려지지 않은 `obs_id`에 대해서도 예외 없이 `None`으로 안전하게 동작한다.
- `local_area`/`obs_id`/`observation_time` 필터가 카탈로그와 client signature에
  모두 드러나 디버그 UI·자동완성에서 발견 가능해졌다.

### 결과(부정)
- `_mountain_stations.py`가 454줄짜리 정적 데이터 파일이라 저장소에 큰 상수
  블록이 추가된다. 벤더가 관측소를 추가·폐지하면 수동으로 갱신해야 한다(자동
  동기화 메커니즘은 없다).
- **정적 표(454개)가 라이브 API의 실제 관측소(약 513개)를 100% 덮지 못한다
  (~88% coverage)** — 라이브로 확인했다. 표에 없는 ~59개 `obs_id`는 좌표
  없이 `None`으로만 남는다. `docs/forest-api.md`와 live test에 이 사실을
  명시했다(전량 커버리지를 가정하지 않도록).

### 후속
- (open) 벤더가 기술문서를 갱신하면(새 관측소 추가 등) `_mountain_stations.py`도
  다시 생성해 동기화해야 한다.
- (open) 라이브 API가 모든 관측소에 대해 지속적으로 `"-"`만 반환하는 이유(승인
  단계 제한인지, 실제 관측 공백인지)는 확인되지 않았다. 운영계정 승인 후
  재확인이 필요하다.
- (open) 정적 표(454개)와 라이브 관측소(약 513개)의 갭(~59개)을 줄이려면
  벤더가 별도 지점 목록 API를 제공하는지 확인하거나, 기술문서 최신판을
  주기적으로 재확인해야 한다.

### 추가(2단계 적대적 리뷰 반영, 2026-09-10)
전문 리뷰어 2명(정확성 관점 + API 설계/컨벤션 관점)의 독립적 리뷰를 거쳐 다음을
반영했다:
- **[확정된 회귀] `client.travel.mountain_weather(local_area=, obs_id=,
  observation_time=)`가 도입되기 전에는 `**params`로 벤더 원본 이름
  (`localArea`/`obsid`/`tm`)을 직접 전달하는 것이 유일한 방법이었다. named
  kwarg를 무조건(`query["localArea"] = local_area`) 대입해 덮어쓰는 최초
  구현은 이 값을 기본값 `None`으로 조용히 지워 기존 호출을 깨뜨렸다(두 리뷰어
  모두 재현). `if x is not None:` 가드로 고쳤고, 같은 문제가 있던
  `dust_measurements(startDt=, endDt=)`도 함께 고쳤다. 회귀 테스트 2건 추가.
- **obsid 필터 자체가 vendor 버그다** — `mountListSearch?obsid=1917`을 라이브
  호출하면 `totalCount=1`인데 `items`가 항상 빈 문자열로 온다. 그래서 live
  test는 이 필터에 의존하지 않고, 필터 없이 받은 배치 중 정적 표에 있는
  항목만 골라 그 값이 표와 일치하는지 검증하도록 다시 작성했다.
- **`obsid` 3901 "괴산 대곡산"이 원본 문서에 충청남도로 잘못 기재**돼 있었다
  (괴산군은 충청북도 소속이고 표의 다른 괴산 관측소 4곳도 모두 충청북도).
  정오표로 보고 충청북도로 바로잡고, 회귀 테스트를 추가했다(리뷰어가 454개
  전체에 대한 지리적 최근접 이웃 일관성 검사로 발견).
- `_http._normalize_payload`의 flat envelope 인식을 JSON(`resultCode`가
  최상위)뿐 아니라 XML(임의의 단일 root tag 바로 아래 `resultCode`가 오는
  경우, 예: 청정넷의 `<ResponseBaseDTO>`)에도 적용하도록 일반화했다 —
  `contentType`을 명시적으로 `xml`로 요청하면(예: Streamlit 디버그 UI의 포맷
  선택) 이전에는 파싱에 실패했다.
- flat envelope 구성 시 `resultMsg`가 없으면 문자열 `"None"`이 에러 메시지에
  새던 것을 고쳤다(`payload.get(k) or ""`).
- `MountainWeather.observed_at`(파싱된 `datetime`)과 이름이 겹치던 client
  파라미터를 `observed_at` → `observation_time`(문자열)으로 바꿨다.
- `obs_name`은 정적 표로 보완하지 않기로 하고 그 fallback을 제거했다(문서화
  범위를 네 필드로 유지하기 위해). `region_name`/`elevation`을
  `latitude`/`longitude`와 나란히 두도록 모델 필드 순서를 바꿨다(같은 세션에
  추가된 `ForestDustStation`의 필드 그룹핑과 일치).
- `tests/test_mountain_stations.py`의 `len(set(MOUNTAIN_STATIONS)) ==
  len(MOUNTAIN_STATIONS)` assertion은 dict 정의상 항상 참인 tautology라
  제거하고, 대신 "괴산" 관측소 5곳이 모두 충청북도인지 확인하는 회귀
  테스트로 대체했다("같은 시/군 접두사는 항상 같은 지역명" 같은 일반 규칙은
  고성(강원/경남)·군위(경북/대구) 같은 정당한 예외가 있어 채택하지 않았다).

### 추가(공개 accessor 도입, 2026-09-10)
리뷰에서 "`MountainWeather`의 docstring이 export되지 않은 내부 모듈
(`_mountain_stations.MOUNTAIN_STATIONS`)을 가리킨다"는 지적(위 리뷰 결과의
finding #14)이 있었고, 곧이어 사용자가 "station 위치 정보도 함께 리턴하도록"
요청했다. 두 요구를 함께 해소하기 위해 정적 참조 테이블을 공개 API로
승격했다.

- 새 공개 모델 `MountainStation`(`obs_id`/`region_name`/`mountain_name`/
  `latitude`/`longitude`/`elevation`, 전부 필수 — `MountainWeather`의 동명
  optional 필드와 달리 참조 테이블 자체는 결측이 없다).
- 새 메서드 `client.travel.mountain_weather_stations() -> tuple[MountainStation, ...]`.
  원격 호출이 없는 로컬 데이터 조회라 `client.catalog()`/`client.endpoints()`
  와 같은 성격의 **동기(sync)** 메서드로 만들었다 — `TravelNamespace`의 다른
  메서드는 전부 async이지만, `ForestClient` 자체에 이미 동기 accessor
  선례가 있어 어색하지 않다고 판단했다.
- `MountainWeather`/`_mountain_stations.py`의 docstring을 이 새 메서드를
  가리키도록 갱신해 더 이상 존재하지 않는(비공개) import 경로를 문서에
  남기지 않는다.
- `obs_id`로 join 가능하도록 오름차순 정렬해 반환한다.

## ADR-011: 취소에 안전한 공통 토큰 버킷

- 상태: accepted
- 날짜: 2026-09-14
- 결정자: Codex

### 컨텍스트

자매 라이브러리의 TPS 의미가 다르고 소수 TPS·취소 경합에서 진행이 멈추는 문제가 있었다.
사용자는 async-only와 동일한 토큰 버킷을 요구했다.

### 결정

외부 런타임 의존성을 추가하지 않고 같은 `AsyncTokenBucket` 소스를 패키지 내부에 둔다.
`asyncio.Lock`을 충전 대기까지 보유하여 FIFO와 취소 처리를 맡기고 별도 timer 큐를 없앤다.
초당 충전량과 burst 용량을 구분하고 명시적으로 한 이벤트 루프에서만 사용한다.
파일 상세 조회, forest.go.kr 팝업 GET·이력 POST·재시도와 최종 다운로드가 같은 버킷을 사용한다.

### 결과

세부 계약과 회귀 테스트는 `docs/async-tps.md`에 기록한다.
독립 리뷰 2건 및 live E2E 성공을 확인한 뒤 PR로 머지한다.
