# CHANGELOG

본 문서는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다. 버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따른다.

## [Unreleased]

`docs/tasks.md`에서 "0.2.0 파괴적 변경을 계기로 도입"으로 계획됐던 문서다. 과거 변경 이력은 `docs/journal.md`와 `docs/decisions.md`(ADR)에 이미 기록되어 있으므로 여기서는 소급 작성하지 않고, 이 시점 이후의 사용자 가시 변경만 기록한다.

### Added

- `client.safety.dust_measurements()`와 `client.safety.dust_stations()`를 추가했다. 청정넷(AICAN) 산림 미세먼지 측정넷의 실시간 PM10/PM2.5/PM1.0·기상 측정값과 관측소 메타데이터(명칭, 좌표, 주소, 장비)를 각각 `ForestDustMeasurement`/`ForestDustStation` typed model로 제공한다. 두 모델의 `station_code`(`obsrr_tpcd`)가 서로의 join key다.
- `ApiEndpoint`/`CatalogEntry`에 `response_type_value` 필드를 추가했다. 응답 타입 파라미터의 값이 provider별로 다른 경우(예: 청정넷의 `contentType=JSON` 대문자 필수) catalog 선언만으로 override할 수 있다.
- `_http._normalize_payload`가 `response.header`/`response.body`로 감싸지 않고 `resultCode`/`items`를 JSON 최상위에 바로 반환하는 응답 envelope(청정넷/AICAN 계열)도 인식하도록 확장했다. 새 endpoint 2건이 이 envelope를 쓰기 때문에 필요했다.

- `MountainWeather`에 `region_name`/`elevation` 필드를 추가했다. `client.travel.mountain_weather()`에 `local_area`/`obs_id`/`observed_at` 파라미터를 추가했다(vendor의 `localArea`/`obsid`/`tm`에 대응).

### Fixed

- `parser.parse_datetime`이 구분자 없는 12자리 `yyyyMMddHHmm` 문자열(예: `mountain_weather`의 `tm`, `wildfire_risk_forecast`의 `analdate`)에서 분(minute) 값을 잘못 파싱하던 기존 버그를 수정했다. `strptime("%Y%m%d%H%M%S")`가 자릿수를 넘나들며 역추적해 예를 들어 `"202511011530"`을 `15:30` 대신 `15:03`으로 잘못 해석했다. 숫자 전용 문자열은 이제 `datetime.fromisoformat`도 거치지 않고 길이(8/10/12/14자리)로만 형식을 고정한다.
- `client.travel.mountain_weather()`가 실제 서비스키로 호출될 때 `latitude`/`longitude`가 항상 `None`이었던 결함을 고쳤다. 실제 `mountListSearch` 응답에는 좌표 필드가 전혀 없는데, 기존 parser는 존재하지 않는 필드(`xValue`/`yValue` 등)를 찾고 있었다. 이제 벤더 기술문서의 관측지점 표(454개, `_mountain_stations.py`)를 `obs_id` 기준으로 조회해 좌표·고도·지역명을 채운다.
- `MountainWeather.wind_direction_10m_name`/`wind_direction_2m_name`이 결측 sentinel 문자열 `"-"`를 그대로 노출하던 것을 `None`으로 고쳤다(같은 API의 숫자 필드는 이미 `None`으로 정규화되고 있었다).
