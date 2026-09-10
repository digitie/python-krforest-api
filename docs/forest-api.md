# Korea Forest Service Travel and Safety Data Scope

This document records the implemented scope. The initial data.go.kr search for
`산림청` returned hundreds of datasets; python-krforest-api narrows that to travel,
outdoor recreation, wildfire, landslide, and forest safety data.

## Client API Shape

- The public client is `httpx`/`asyncio` based and follows the
  `python-krheritage-api` style: create `ForestClient(api_key=...)` or
  `ForestClient.from_env()`, use `async with`, and call public methods with
  `await client.travel...`, `await client.safety...`, or `await client.files...`.
- Compatibility shims for older sync usage are intentionally not provided here;
  downstream consumers such as `python-krtour-map` should use the stabilized
  async public API directly.
- The supported key environment variable is `DATA_GO_KR_SERVICE_KEY`. Legacy
  fallback environment variable names are intentionally not supported.

## Implemented OpenAPI Endpoints

| Key | Category | Provider | data.go.kr | Operation |
| --- | --- | --- | --- | --- |
| `forest_trail_services` | travel | forest.go.kr | 15002725 | `trailInfoService/getforestservice` |
| `mountain_stories` | travel, safety | forest.go.kr | 15058682 | `trailInfoService/getforeststoryservice` |
| `forest_spatial_trails` | travel | forest.go.kr | 15002734 | `trailInfoService/getforestspatialdataservice` |
| `baekdu_trails` | travel | forest.go.kr | 15002731 | `trailInfoService/gettrailservice` |
| `famous_mountain_trails` | travel | forest.go.kr | 3071170 | `cultureInfoService/gdTrailInfoImgOpenAPI` |
| `mountain_weather` | travel, safety | data.go.kr | 15084696 | `1400377/mtweather/mountListSearch` |
| `national_recreation_forest_reservations` | travel | data.go.kr | 15134227 | `1400000/nationalRecreationForestReservationService/nationalRecreationForestReservationList` |
| `standard_recreation_forests` | travel | data.go.kr | 15013111 | `openapi/tn_pubr_public_rcrfrst_api` |
| `wildfire_risk_forecast` | safety | data.go.kr | 15084817 | `1400377/forestPointV2/forestPointListGeongugSearchV2` |
| `wildfire_risk_forecast_sido` | safety | data.go.kr | 15084817 | `1400377/forestPointV2/forestPointListSidoSearchV2` |
| `wildfire_risk_forecast_sigungu` | safety | data.go.kr | 15084817 | `1400377/forestPointV2/forestPointListSigunguSearchV2` |
| `wildfire_stats` | safety | data.go.kr | 3070842 | `1400000/forestStusService/getfirestatsservice` |
| `past_landslides` | safety | data.go.kr | 15074816 | `1400000/pastLndslInfoService/pastLndslInfoList` |
| `landslide_predictions` | safety | data.go.kr | 15074800 | `1400000/predictionInfoService/predictionInfoList` |
| `landslide_forecast_issues` | safety | data.go.kr | 15074798 | `1400000/forecastIssueService/forecastIssueList` |
| `roadside_landslides` | safety | data.go.kr | 15074812 | `1400000/roadsideLndslInfoService/roadsideLndslInfoList` |
| `erosion_control_dams` | safety | data.go.kr | 15074803 | `1400000/ecndmInfoService/ecndmInfoList` |
| `forest_dust_measurements` | safety | data.go.kr | 15078005 | `1400377/AicanDustData/dustData` |
| `forest_dust_stations` | safety | data.go.kr | 15078013 | `1400377/AicanObsrrInfo/obsrrInfo` |

Notes:

- `forest.go.kr` legacy endpoints currently return XML and work with the
  tripmate data.go.kr key.
- Some `apis.data.go.kr/1400000` and `1400377` endpoints returned HTTP 403 with
  the checked tripmate key on 2026-05-08. The client still implements them
  because they are public endpoints, but live tests mark missing approval
  cleanly as authorization xfail.
- `national_recreation_forest_reservations` uses the official
  `serviceKey` query parameter name and returns XML reservation status items
  with institution, goods, stay date, and status fields.
- `standard_recreation_forests` uses the standard data endpoint
  `https://api.data.go.kr/openapi/tn_pubr_public_rcrfrst_api`, the official
  `serviceKey` parameter, and `type=json`. The detail page may redirect through
  the data.go.kr login/application flow.
- `client.travel.mountain_weather()` returns `MountainWeather` typed observations.
  The model exposes station identity, KST-aware observation time, 10 m/2 m
  temperature-humidity-wind fields, pressure and rainfall fields, while raw
  provider keys remain in `raw`. Accepts `local_area` (지역코드 01~17), `obs_id`
  (지점번호), and `observation_time` (정확한 관측시간 `yyyyMMddHHmm`, not to be
  confused with the parsed `datetime` in `MountainWeather.observed_at`) as
  optional filters, mapped to the vendor's `localArea`/`obsid`/`tm` params.
  개발계정 신청 가능 트래픽은 10,000회/일이다(청정넷/AICAN 계열의 1,000회/일과
  다르다). **Note:** the vendor's `obsid` filter itself is broken — a live call
  returns `totalCount=1` with an empty `items` list — so don't rely on it to
  fetch a single known station; filter client-side instead.
  - **The live `mountListSearch` response never includes coordinates, elevation,
    or a region name** — confirmed both from the vendor's technical document
    (`03_산악기상정보_기술문서_v1.5(수정본).docx`, response field table) and by a
    real API call. `latitude`/`longitude`/`elevation`/`region_name` are instead
    looked up by `obs_id` from a 454-entry static table (transcribed from that
    document's "지점 상세 코드" appendix) — `obs_name` is NOT enriched this way
    and is always the response's own value. If the response ever does carry
    coordinate fields directly (future provider change), those take priority
    over the static table. An unknown `obs_id` leaves these four fields `None`
    rather than raising.
  - `client.travel.mountain_weather_stations()` returns that same 454-station
    static table directly as `MountainStation` records (`obs_id`, `region_name`,
    `mountain_name`, `latitude`, `longitude`, `elevation`, all required —
    unlike `MountainWeather`'s optional versions of the same four fields). It's
    a **synchronous, local-only** method (no HTTP call, matching
    `client.catalog()`/`client.endpoints()`), sorted by `obs_id` ascending, and
    is the supported way to enumerate or join against the reference data instead
    of importing the internal `_mountain_stations` module.
  - **Coverage gap:** the live API currently returns roughly 513 stations, but
    the static table has only 454 rows (~88% coverage) — the vendor's technical
    document appendix is itself a snapshot and lags the live registry. Don't
    assume every returned row gets coordinates; check `latitude is not None`
    per item.
  - The live response uses the literal string `"-"` as its missing-value
    sentinel for every dynamic field (temperature, humidity, wind, rainfall,
    pressure, observation time) — confirmed live: at the time of this review,
    *every* one of the ~513 stations returned `"-"` for all of them. Numeric
    fields already become `None` as a side effect of `float("-")` raising
    `ValueError`; `wind_direction_10m_name`/`wind_direction_2m_name` (string
    compass-direction fields) needed an explicit `_none_if_dash` check in
    `parser.py` since they have no such numeric conversion to fall back on.
- `client.safety.wildfire_risk_forecast()`, `_sido()`, and `_sigungu()` use the
  official `forestPointV2` endpoints and return `WildfireRiskForecast` typed
  rows. `localAreas` and `upplocalcd` are passed only to the corresponding
  regional endpoints.
- `client.safety.landslide_forecast_issues()` returns
  `LandslideForecastIssue` typed rows with issue kind, issuing institution,
  status, and KST-aware first issue time.
- `client.travel.recreation_forests()` combines the national recreation forest
  promotion, facility, reservation policy, and reservation file datasets into a
  high-level detail record with plain `address`, `latitude`, and `longitude`
  fields.
- `client.travel.kid_forest_centers()` and
  `client.travel.recreation_forest_arboretums()` download forest.go.kr SHP ZIP
  files, submit the popup purpose as `개인자료용` (`dnldPrps=3`), and return
  `ForestSpatialPoint` records with `address`, plus transformed WGS84
  `latitude` and `longitude` floats.
- `client.travel.forest_education_centers()` and
  `client.travel.traditional_village_forests()` apply the same forest.go.kr
  download flow and return `ForestSpatialPoint` records.
- `client.travel.forest_trail_file_features()` and
  `client.travel.dulle_trail_features()` download the forest.go.kr aggregate ZIP
  files and return `ForestSpatialFeature` records with WGS84 geometry metadata.
  `PBD0000041` is an aggregate archive: the canonical SHP layers are nested in
  one ZIP per region, while sibling `_geojson.zip`/`_gpx.zip` archives contain
  alternate copies and are not emitted a second time. Each emitted record has
  a non-null, reproducible opaque `source_id` scoped to the dataset. The key is
  a fingerprint of the source file and all available stable source fields
  (`PMNTN_SN`, `Name`, `ID`, and similar); geometry is used only when no source
  identity exists. Exact duplicate rows are first-wins deduplicated. The route
  name combines `MNTN_NM` and `PMNTN_NM` when both are available.
- `client.safety.landslide_risk_map_files()` downloads the forest.go.kr
  산사태위험지도 ZIP and returns a filename-keyed `dict[str, bytes]` because the
  dataset is raster TIF/XML/PDF rather than record-shaped vector data.
- `client.safety.dust_measurements()` and `client.safety.dust_stations()` wrap
  국립산림과학원_청정넷(AICAN, 산림 미세먼지 측정넷) and return `ForestDustMeasurement`
  / `ForestDustStation` typed rows. Both models expose `station_code` (from
  `obsrr_tpcd`) as the join key between a measurement row and its station —
  `obsrr_group_cd` (site grouping such as 홍릉/고매/시화/양재/관악/제주) only exists
  on the station side. `ForestDustStation.installed_at` stays a plain `yyyyMMdd`
  string (not `datetime`) because the vendor only provides day precision; a
  KST-midnight `datetime` would shift a day when a consumer converts to another
  timezone. Both endpoints return a *flat* envelope (`resultCode`/`resultMsg`/
  `items` at the JSON root, no `response.header/body` wrapper). This vendor's
  XML also lacks the usual `<response>` root tag — it uses `<ResponseBaseDTO>`
  with `resultCode` directly underneath — so `_http._normalize_payload`
  recognizes a flat envelope under *either* encoding: `resultCode` at the JSON
  root, or one level under any single XML root tag. This matters if a caller
  explicitly requests `response_format="xml"` (e.g. via the Streamlit debug
  UI's format dropdown) for these two endpoints. Both endpoints also require
  the literal
  uppercase `contentType=JSON` — lowercase `json` silently falls back to XML —
  so `ApiEndpoint.response_type_value` was added to override the default
  lowercase `"json"` value per endpoint. 개발계정 신청 가능 트래픽은 두 endpoint
  모두 1,000회/일이며, 운영계정은 활용사례 등록 후 증설 신청이 가능하다(2026-09-09
  data.go.kr 상세 페이지 확인). `dust_stations()`는 같은 API의 지도 조회 기능인
  `obsrrInfoWms`(WMS 이미지)와 `obsrrInfoWFS`(GML feature)는 구현하지 않고, JSON
  속성 조회(`obsrrInfo`)만 구현한다 — 이 라이브러리는 이미지/GML을 다루지 않는다.
- `parse_datetime`이 구분자 없는 숫자열(`yyyyMMddHHmm` 등)에서 `strptime`의
  `%Y%m%d%H%M%S` 형식이 자릿수를 잘못 역추적해 분(minute) 값을 훼손하던 버그를
  고쳤다(예: `"202511011530"` → 이전에는 `15:03`, 이제 `15:30`). 숫자 전용
  문자열은 이제 `datetime.fromisoformat`을 거치지 않고 길이(8/10/12/14자리)로만
  형식을 고정해서 파싱한다 — `fromisoformat`도 11/13/15자리 같은 애매한 길이의
  숫자열에서는 구분자를 잘못 추정해 같은 종류의 오류를 낼 수 있기 때문이다. 이
  버그는 `mountain_weather`, `wildfire_risk_forecast` 등 12자리 타임스탬프를 쓰는
  기존 endpoint에도 영향을 미쳤었다.

## Implemented File Datasets

| data.go.kr | Category | Format | Dataset |
| --- | --- | --- | --- |
| PBD0000041 | travel | SHP, GPX, GEOJSON, ZIP | 산림청 등산로정보 ZIP |
| PBD0000031 | travel | SHP, GPX, ZIP | 산림청 숲길정보 ZIP |
| PBD0000221 | travel | SHP, ZIP | 산림청 산림교육센터 현황 SHP |
| PBD0000220 | travel | SHP, ZIP | 산림청 유아숲체험원 현황 SHP |
| PBD0000077 | travel | SHP, ZIP | 산림청 전통마을숲 위치도 SHP |
| PBD0000180 | travel | SHP, ZIP | 산림청 휴양림수목원 위치도 SHP |
| PBD0000210 | safety | TIF, XML, PDF, ZIP | 산림청 산사태위험지도 ZIP |
| 15112801 | travel | CSV | 산림청 국립자연휴양림관리소_숲나들e 숲길 100대명산 정보 |
| 3034022 | travel | SHP | 산림청_등산로(산림문화·휴양정보) |
| 3034163 | travel | SHP | 산림청_숲길(산림문화·휴양정보) |
| 15098177 | travel | GPX | 한국등산트레킹지원센터_산림청 100대명산 |
| 15041973 | travel | SHP | 산림청_휴양림수목원 위치도 |
| 15064415 | travel | CSV | 국립자연휴양림 홍보 |
| 15064419 | travel | CSV | 국립자연휴양림 시설관련 정보 |
| 15064416 | travel | CSV | 국립자연휴양림 예약 정책 |
| 15064418 | travel | CSV | 국립자연휴양림 예약 정보 |
| 15113956 | travel | CSV | 명품숲길정보 |
| 15113562 | travel | CSV | 숲나들e 숲길정보 |
| 15110618 | travel | CSV | 국가숲길 이용등급 데이터 |
| 15141659 | travel | SHP | 국가숲길 노선도 데이터(한라산둘레길) |
| 15141660 | travel | SHP | 국가숲길 노선도 데이터(속리산둘레길) |
| 15074817 | safety | IMG, XML | 산사태위험지도 |
| 15121380 | safety | CSV | 산불통계데이터 |
| 15125006 | safety | CSV | 최근 5년간 전국 산사태 발생 이력 |
| 15072172 | safety | XLS | 산사태예보발령 |
| 15120930 | safety | CSV | 산사태정보 실황정보 |
| 15092027 | safety | CSV | 대형산불위험예보목록정보 |
| 15092032 | safety | CSV | 동해안산불위험예보정보 |
| 15125648 | safety | PNG | 산불위험예보분석이미지 |
| 15125640 | safety | PNG | 산불위험실황분석이미지 |
| 15121208 | safety | CSV | 산불신고 유형별 위험지수 |
| 15144785 | safety | CSV | 산불소화시설 |
| 15144788 | safety | CSV | 진화대원대기장소 |
| 15144784 | safety | CSV | 담수용사방댐 |

## 공간 피처 정규화 규칙

`ForestSpatialFeature`는 원천 파일의 `source_file`, `layer_name`, `source_id`,
`geometry_type`, GeoJSON 형태의 `geometry`, WGS84 `bbox`·중심 좌표와 정제되지 않은
`raw` 필드를 함께 보존한다. 지도 소비자는 `LineString`과 `MultiLineString`만 경로로
승격해야 하며, `Point`·다각형·빈 도형은 경로로 추정하지 않는다. 산림청 파일은 노선의
폐쇄·통행 가능 여부를 실시간으로 보장하지 않으므로 이 모델에 운영 상태를 만들어내지
않는다.

## Exclusions

Excluded examples include pure biology/specimen catalogs, forestry economics,
legal interpretation, business registration, and local-government datasets that
only mention 산림청 in their descriptions. The GPX 100대명산 file dataset is
included because it directly supports hiking/travel use.

### 2026-09-09 국립산림과학원 20-API catalog review

A sibling project's API-coverage catalog (`산림청 국립산림과학원`, 20 datasets across
data.go.kr ids `15078005`–`15156604`, not a contiguous range) was reviewed
against this scope. Only 4 of the 20 datasets fit travel/safety and are
implemented, as 6 endpoints: `mountain_weather` and the 3
`wildfire_risk_forecast*` endpoints (already present, 1 dataset id) plus the 2
new `forest_dust_measurements`/`forest_dust_stations` endpoints added in this
review (청정넷/AICAN 산림 미세먼지 실측 데이터, air quality is actionable safety
information for anyone deciding whether to go outdoors). The remaining 16
datasets were evaluated and intentionally excluded:

| data.go.kr id | 이름 | 제외 사유 |
| --- | --- | --- |
| 15084717 | 산림생명자원 | 표본·종자·보존림 생물 카탈로그 (specimen catalog) |
| 15083722 | 산림생장정보 | 입목재적·임분수확표 (forestry biomass/economics reference tables) |
| 15083744 | 임업기술핸드북 | 임업 기술 참고문헌 (reference handbook, not travel/safety data) |
| 15084708 | 산림연구 과제 및 성과 정보 | 연구과제·논문·특허 정보 (research/academic) |
| 15083696 | 임업경제동향 | 원목 가격 동향 (forestry economics) |
| 15084808 | 산림과학도서관 | 도서관 소장자료 검색 (library catalog) |
| 15083709 | 목재류 비관세장벽 현황정보 | 목재 소비·GDP 통계 (forestry economics) |
| 15156601 | 주요수종목재도감 상세 | 수종·목재 도감 (specimen/reference catalog) |
| 15156597 | 절지동물분포조사자료 | 절지동물 분포조사 (biology/specimen survey) |
| 15156594 | 식물정유은행 | 식물 정유 성분 데이터 (biology/specimen catalog) |
| 15156592 | 대나무자원정보 | 대나무 표준지 조사자료 (biology/resource survey) |
| 15156604 | 한국임목종자도감 | 임목종자 형질 도감 (specimen/reference catalog) |
| 15078022 | 청정넷_그린인프라 | 도시조사지역·임목·표본점 WMS/WFS 공간 레이어. 홍릉·고매·시화·양재·관악·제주 6개 연구 대상지에 한정된 도시숲 연구용 GIS 레이어이며, 실측값이 아니라 정적 분류 레이어라 여행자에게 실행 가능한 정보를 주지 않는다 |
| 15078027 | 청정넷_그레이인프라 | 나지·다리·건물·하천·도로 WMS/WFS 레이어. 위와 동일한 사유(연구 대상지 한정, 정적 인프라 분류) |
| 15078028 | 청정넷_사용자가치 | 토지피복·인구밀도·교통속도 가중치 WMS/WFS 레이어. 위와 동일한 사유 |
| 15080323 | 청정넷_유관기관 변환자료 | 2020년 4개 지점(홍릉·고매·시화·양재)의 DEM·유동인구·교통량 연구 데이터. 여행자용 실시간 정보가 아닌 과거 연구 맥락 데이터 |

`forest_dust_stations`가 구현하는 `AicanObsrrInfo` API 자체는 속성 조회
(`obsrrInfo`) 외에 WMS(`obsrrInfoWms`)와 WFS(`obsrrInfoWFS`) 지도 조회 기능도
제공하지만, 이미지·GML 응답은 이 라이브러리의 typed-JSON 모델 구조와 맞지 않아
구현하지 않았다(위 4개 청정넷 GIS API를 제외한 사유와 동일).
