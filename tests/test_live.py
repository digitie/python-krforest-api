from __future__ import annotations

import os

import pytest

from krforest import ForestAuthError, ForestClient
from krforest._mountain_stations import MOUNTAIN_STATIONS

pytestmark = pytest.mark.live

LIVE_TIMEOUT = 60


def _service_key() -> str:
    value = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if value:
        return value
    pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")


async def test_live_legacy_forest_services_returns_items():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    page = await client.travel.forest_services(num_of_rows=1)

    assert page.page_no >= 1
    assert page.num_of_rows >= 1
    assert page.total_count >= len(page.items)
    assert page.context.provider == "forest.go.kr"
    assert page.context.endpoint == "getforestservice"
    assert "ServiceKey" not in page.context.request_params
    assert key not in repr(page.context.request_params)
    assert page.items


async def test_live_file_dataset_download_url_is_discoverable():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    url = await client.files.download_url("15112801")

    assert url.startswith("https://www.data.go.kr/cmm/cmm/fileDownload.do")
    assert "atchFileId=" in url
    assert "fileDetailSn=" in url


async def test_live_data_go_safety_endpoint_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.wildfire_stats(
            search_start_date="20240101",
            search_end_date="20241231",
            num_of_rows=1,
        )
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 1400000 forest safety APIs are not approved for this key")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.total_count >= len(page.items)


async def test_live_mountain_weather_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        # obsid 필터는 vendor 측 버그로 totalCount=1인데 items가 항상 비어
        # 반환된다(라이브로 확인). 그 필터에 의존하지 않고, 필터 없이 받은
        # 배치 중 정적 참조 테이블에 있는 항목만 골라 그 값이 표와 일치하는지
        # 확인한다 — 표(454개)가 라이브 관측소 전체(약 513개, ADR-010 참조)를
        # 100% 덮지 않으므로 "전부 좌표가 있어야 한다"고 가정하지 않는다.
        page = await client.travel.mountain_weather(num_of_rows=20)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15084696 mountain weather API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "mountListSearch"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)
        assert page.items
        covered = [item for item in page.items if item.obs_id in MOUNTAIN_STATIONS]
        assert covered, "no station in this batch was found in the static reference table"
        for item in covered:
            expected = MOUNTAIN_STATIONS[item.obs_id]
            assert item.latitude == expected.latitude
            assert item.longitude == expected.longitude
            assert item.elevation == expected.elevation
            assert item.region_name == expected.region_name


async def test_live_wildfire_risk_v2_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.wildfire_risk_forecast(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15084817 V2 wildfire risk API is not approved")
    else:
        assert page.context.endpoint == "forestPointListGeongugSearchV2"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)


async def test_live_landslide_forecast_issues_are_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.landslide_forecast_issues(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15074798 landslide forecast API is not approved")
    else:
        assert page.context.endpoint == "forecastIssueList"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)


async def test_live_recreation_forest_reservations_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.travel.recreation_forest_reservations(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15134227 recreation forest reservation API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "nationalRecreationForestReservationList"
        assert "serviceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)


async def test_live_forest_education_centers_download_and_parse():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    records = await client.travel.forest_education_centers()

    assert records
    assert records[0].dataset_id == "PBD0000221"
    assert records[0].latitude is not None
    assert records[0].longitude is not None


async def test_live_dulle_trail_features_are_line_features_with_source_ids():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    features = await client.travel.dulle_trail_features()

    line_features = [
        feature
        for feature in features
        if feature.geometry_type in {"LineString", "MultiLineString"}
    ]
    assert line_features
    assert all(feature.source_id for feature in line_features)
    assert all(feature.geometry for feature in line_features)


async def test_live_mountain_trail_features_are_line_features_with_source_ids():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    features = await client.travel.forest_trail_file_features()

    assert features
    assert all(
        feature.geometry_type in {"LineString", "MultiLineString"} for feature in features
    )
    assert all(feature.source_id for feature in features)
    assert all(feature.geometry for feature in features)


async def test_live_dust_measurements_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.dust_measurements(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15078005 청정넷 측정데이터 API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "dustData"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)
        assert page.items
        assert page.items[0].observed_at is not None


async def test_live_dust_stations_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.dust_stations(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15078013 청정넷 운영현황 API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "obsrrInfo"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)


async def test_live_landslide_risk_map_archive_downloads_files():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    files = await client.safety.landslide_risk_map_files()

    assert any(name.endswith(".tif") for name in files)
    assert any(name.endswith(".xml") for name in files)
