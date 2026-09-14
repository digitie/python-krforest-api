# Resume

현재 `python-krforest-api` 프로젝트의 진척도와 이어서 할 작업을 기록합니다. 새 세션이나 작업 재개 시 이 문서를 가장 먼저 확인하세요.

## 2026-09-14 TPS 통합 검증 완료

- 파일 상세 조회, forest.go.kr 팝업 GET·이력 POST·재시도와 최종 다운로드가 같은 버킷을 사용한다.
- 공통 계약과 회귀 테스트는 `docs/async-tps.md`를 참고한다.
- 오프라인 pytest 82 passed, ruff/mypy/compileall 통과. 독립 적대적 리뷰 2건의 수정 사항을 반영하고 승인받았다.
- 실제 공급자 live E2E: 12 passed, 1 xfailed (1400000 safety API 사용 승인 부족). xfail은 성공 건수에 포함하지 않는다.
- WSL에서 확인한 취소 테스트의 10ms 타이밍 의존성을 Event와 가짜 시계로 제거했고 8개 버킷 테스트가 통과했다.

## 현재 진척도 (2026-09-10)

- `client.travel.mountain_weather()`의 실사용 결함을 고쳤다: 실제
  `mountListSearch` 응답에는 좌표·고도·지역명 필드가 전혀 없어(벤더 기술문서 +
  라이브 호출로 확인) 좌표가 항상 `None`이었다. 기술문서 부록의 관측지점 표
  454개를 `src/krforest/_mountain_stations.py`로 옮기고, `obs_id` 기준으로
  조회해 `latitude`/`longitude`/`elevation`/`region_name`을 채운다. ADR-010.
- 결측 sentinel 문자열 `"-"`가 문자열 필드(`wind_direction_10m_name`/
  `wind_direction_2m_name`)에는 그대로 남아 있던 것을 `_none_if_dash`로 고쳤다
  (숫자 필드는 이미 `ValueError` 부작용으로 우연히 `None`이었다).
- `localArea`/`obsid`/`tm`을 `catalog.py` `optional_params`에 채우고
  `client.travel.mountain_weather(local_area=, obs_id=, observation_time=)`
  named kwarg를 추가했다. 개발계정 트래픽 한도(10,000회/일, 청정넷과 다름)도
  확인해 기록했다.
- **새 공개 API**: `MountainStation` 모델과
  `client.travel.mountain_weather_stations()`(동기, 로컬 데이터)를 추가해
  454개 관측지점 참조 테이블을 직접 조회할 수 있게 했다.
- **PR 머지 전 2단계 적대적 리뷰(정확성 + 설계/컨벤션 관점, 각각 독립적으로
  전체 diff 검토) 반영 완료**: 두 리뷰어가 공통으로 재현한 회귀
  (named kwarg가 `**params`로 전달된 vendor 원본 파라미터명을 조용히
  덮어쓰던 문제, `mountain_weather`와 `dust_measurements` 둘 다), 정확성
  리뷰어가 454개 표 전체 지리 일관성 검사로 찾은 obsid 3901 지역명 오류
  (충청남도→충청북도 정오표 수정), 청정넷 XML root tag(`<ResponseBaseDTO>`)
  파싱 실패, flat envelope `resultMsg` 없을 때 `"None"` 누출, `mountain_weather`
  의 `obsid` 필터 자체가 vendor 버그(`totalCount=1`인데 `items` 항상 빈
  문자열)임을 확인해 그 필터에 의존하지 않도록 live test 재작성 등을 모두
  고쳤다. ADR-010 "추가" 절 참조.
- 정적 표(454개)가 라이브 관측소 전체(약 513개)를 100% 덮지 않음(~88%
  coverage)을 확인해 문서·테스트 전반에 명시했다(100% 커버리지를 가정하지
  않도록).
- `pytest -q` 66 passed / live 11 passed·2 xfailed, `ruff`, `mypy --strict` 통과.

## 다음 해야 할 작업 (Next Task)

- [ ] 리뷰·수정 완료 — PR 생성 및 CI 확인 후 머지.
- [ ] 운영계정 승인 또는 다른 시점에 `mountain_weather` 라이브 데이터를 재확인해
  `"-"` 전역 결측이 승인 단계 문제인지 실제 공백인지 판별.
- [ ] `_mountain_stations.py`는 벤더 기술문서 스냅샷이라 자동 동기화 메커니즘이
  없다 — 벤더가 관측소를 추가/폐지하면 수동 재생성 필요. 정적 표(454개)와
  라이브 관측소(약 513개)의 갭(~59개)을 줄일 방법도 확인 필요.

## 현재 진척도 (2026-09-09)

- `산림청 국립산림과학원` 20-API 카탈로그를 검토해 `forest_dust_measurements`
  (15078005)와 `forest_dust_stations`(15078013, 청정넷/AICAN 산림 미세먼지)를
  safety endpoint로 추가했다. 나머지 16건은 기존 범위 제외 기준에 따라
  `docs/forest-api.md` Exclusions와 ADR-009에 사유를 기록하고 구현하지 않았다.
- 이 과정에서 `_http._normalize_payload`가 `resultCode`/`items`를 최상위에 바로
  반환하는 flat envelope(response.header/body로 감싸지 않는 형태)도 지원하도록
  확장했고, `ApiEndpoint.response_type_value`를 추가해 `contentType=JSON`처럼
  provider별 대소문자/값이 다른 응답 타입 파라미터를 catalog 선언만으로 표현할 수
  있게 했다.
- 라이브 검증 중 `parser.parse_datetime`이 구분자 없는 12자리 `yyyyMMddHHmm`
  문자열의 분(minute) 값을 `strptime("%Y%m%d%H%M%S")` 자릿수 역추적으로 훼손하던
  기존 버그를 발견·수정했다. `mountain_weather`/`wildfire_risk_forecast` 등 기존
  12자리 타임스탬프 필드에도 영향을 미치던 버그였다.
- 실제 서비스키로 `client.safety.dust_measurements()` 라이브 호출을 확인했다
  (활용신청 승인 상태, 총 30,286,187건). `dust_stations()`는 아직 활용신청
  미승인이라 auth xfail(기존 다른 `1400377`/`1400000` endpoint와 동일 패턴).
- `pytest -q` 49 passed / live 11 passed·2 xfailed(환경변수 설정 시), `ruff`와
  `mypy --strict src/krforest` 통과.

## 다음 해야 할 작업 (Next Task)

- [x] 전문 리뷰어 2명의 독립적 적대적 리뷰(정확성 관점 + API 설계/컨벤션 관점)를
  반영: pydantic `model_` 네임스페이스 충돌 회피(`equipment_reference_number`),
  join key 이름 정정(`station_type_code`→`station_code`), 날짜 전용 필드를
  `datetime`이 아닌 문자열로 노출(`installed_at`), `_convert.extract_address`
  사용 일관화, `parse_datetime`이 `fromisoformat`도 우회하도록 강화(11/13/15자리
  숫자열 오파싱 방지), flat envelope 성공/실패 경로와 기존 12자리 타임스탬프
  회귀 테스트 보강, 라이브 키 검증 테스트의 `serviceKey`→`ServiceKey` 대소문자
  오류 수정, ADR-009/`forest-api.md`의 수치 불일치(나머지 16건/12건, 4 dataset vs
  6 endpoint) 정정. PR CI·머지는 아직 남음.
- [ ] (백로그) 청정넷 GIS 레이어(WMS/WFS, 그린/그레이인프라·사용자가치·유관기관
  변환자료 4건)나 나머지 12개 비-GIS 국립산림과학원 API(생물표본·임업경제·
  도서관/연구) 중 travel/safety use case가 생기면 ADR-009와
  `docs/forest-api.md` Exclusions를 갱신한 뒤 재검토.

## 현재 진척도 (2026-08-20)

- `T-VN-C05A`의 forest.go.kr `PBD0000041` 통합 ZIP을 구현 계약에 맞게 보강함.
  지역별 중첩 ZIP의 canonical SHP를 재귀적으로 읽고 `_geojson.zip`·`_gpx.zip` 형제
  사본은 중복 방지를 위해 건너뛴다.
- `ForestSpatialFeature.source_id`를 추가하고, 산행로는 `PMNTN_SN`, 둘레길은 원천
  세그먼트 식별자를 우선 사용한다. 산 이름과 구간 이름(`MNTN_NM`·`PMNTN_NM`)도
  표시명으로 결합한다.
- 실측 census(2026-08-20): PBD0000041 265,601,808 bytes, 중첩 SHP ZIP 2,932개,
  원천 피처 164,185개(Point 107,125 / LineString 56,869 / MultiLineString 191),
  그중 완전 중복 3건을 first-wins 제거하면 공개 피처는 164,182개다. 지도 경로
  승격 대상은 LineString/MultiLineString이다.
- 반복적인 CRS 생성 비용을 줄이기 위해 `_coordinate_transformer`를 캐시한다. 저메모리
  census는 완료했으며, 전체 DTO materialization은 지도 ETL에서 필요한 geometry gate와
  중복 제거를 먼저 확정한 뒤 별도 live 검증한다.
- route-only live parse(2026-08-20)는 `forest_trail_file_features()`에서 Point를
  만들지 않고 LineString 56,869개와 MultiLineString 191개, 총 57,060개를 반환했다.
  이름·geometry·source_id가 모두 채워졌고 source_id 고유값도 57,060개였다.
- 중첩 SHP 회귀 테스트와 `ruff check .`가 통과했다. 둘레길 source-id live test는
  서비스키가 있는 환경에서 실행한다.
- C05B 산악기상, C05C 산불위험 V2(전국·시도·시군구), C05D 산사태 예보발령을
  typed model/parser/client로 구현했다. 산불 시군구 응답은 `sigucode`를 지역 코드로
  우선 사용하며, provider body-level 인증 오류와 Name-only 공간 피처의 ID 충돌도
  보완했다.
- 전체 provider 단위 테스트 42 passed, live 11 skipped(환경변수 미설정), `ruff`와
  `mypy --strict src/krforest`가 통과했다.

## 다음 해야 할 작업 (Next Task)

- [ ] 전문 리뷰어 2명의 독립적 적대적 리뷰를 모두 반영한 뒤 PR CI·머지.
- [ ] `kor-travel-map`에서 C05A route 및 C05B~C05D safety ETL 연결과 schedule을
  구현하고 provider pin을 병합 SHA로 갱신.

## 현재 진척도 (2026-06-07)

- `src/krforest/debug.py`의 `save_fixture`에서 파일을 저장할 때 로컬 저장과 함께 `rustfs`에도 저장할 수 있도록 코드를 개선함.
- 호환성 확보를 위해 기존 API 외에 `rustfs` 호출을 위한 전용 함수 `save_to_rustfs`를 추가함.
- **`python-kraddr-base` 의존성 완전 제거.** 좌표는 `latitude: float | None` / `longitude: float | None`, 주소는 `address: str | None`로 평탄화되어 외부 도메인 패키지 없이 동작함. ADR-008.
- `_convert.py`에 `extract_coordinate(row)` / `extract_address(row)` 헬퍼 추가. 결측 sentinel(-99, -999, 0)을 일관 처리.
- `__version__`을 `0.2.0`으로 올림(파괴적 변경). 호환성 부담 의도적으로 단절.
- `pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. mypy 외부 경로 설정도 함께 제거.
- 이전 작업(2026-05-24)에서 정착한 문서 방법론(`SKILL.md`, ADR, journal, resume, tasks)은 그대로 유지하며 ADR-008 추가.
- 에이전트 작업 규칙에 Windows Git(`C:\Program Files\Git\cmd\git.exe`) 사용 원칙을 명시했고, `.codegraph`는 gitignore 대상임을 다시 고정했다.

## 다음 해야 할 작업 (Next Task)

- [ ] PR 본문에 ADR-008 링크와 마이그레이션 가이드(필드명 변경) 정리 후 main에 머지.
- [ ] (백로그) 데이터 반환 스키마 최적화 및 fixture 보강 — `docs/tasks.md` 참조.
- [ ] (백로그) 신규 파일데이터 endpoint 카탈로그 등록.
- [ ] (백로그) `_convert.extract_address`가 주소 문자열만 다루므로, 도로명/지번 분리가 필요한 사용자 시나리오가 생기면 별도 헬퍼 검토.
