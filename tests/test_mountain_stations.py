from __future__ import annotations

from krforest import MountainStation
from krforest._mountain_stations import MOUNTAIN_STATIONS, mountain_stations


def test_mountain_stations_table_has_expected_size():
    # 454는 소스 문서의 행 수와 일치해야 한다. dict literal에서 obs_id 키가
    # 중복되면 나중 값이 앞 값을 조용히 덮어써 카운트가 454보다 작아지므로, 이
    # 검사가 곧 키 유일성 검사이기도 하다(len(set(dict)) == len(dict)는 dict
    # 정의상 항상 참이라 별도 assertion으로는 아무것도 검증하지 못한다).
    assert len(MOUNTAIN_STATIONS) == 454


def test_mountain_stations_coordinates_are_within_korea_bounds():
    for station in MOUNTAIN_STATIONS.values():
        assert 33.0 <= station.latitude <= 39.0
        assert 124.0 <= station.longitude <= 132.0
        assert station.elevation >= 0.0
        assert station.region_name
        assert station.mountain_name


def test_mountain_stations_known_entries_match_vendor_spec():
    # data.go.kr 15084696 기술문서(03_산악기상정보_기술문서_v1.5(수정본).docx)의
    # "지점 상세 코드" 표에서 직접 확인한 값.
    hongneung = MOUNTAIN_STATIONS["1910"]
    assert hongneung.region_name == "서울특별시"
    assert hongneung.mountain_name == "홍릉수목원임외"
    assert (hongneung.latitude, hongneung.longitude, hongneung.elevation) == (
        37.59,
        127.04,
        36.0,
    )

    gwanaksan = MOUNTAIN_STATIONS["1917"]
    assert gwanaksan.region_name == "서울특별시"
    assert gwanaksan.mountain_name == "서울 관악산"
    assert (gwanaksan.latitude, gwanaksan.longitude, gwanaksan.elevation) == (
        37.45,
        126.93,
        382.0,
    )

    # 원본 문서에 각주성 백틱(``)이 붙어 있던 항목 — 정리되어 있어야 한다.
    changnyeong = MOUNTAIN_STATIONS["8898"]
    assert changnyeong.mountain_name == "창녕 영취산(병봉)"
    assert "`" not in changnyeong.mountain_name

    # obsid 3901 "괴산 대곡산"은 원본 문서에 충청남도로 잘못 기재되어 있었다
    # (괴산군은 충청북도 소속이고, 이 표의 다른 "괴산" 관측소 4곳도 모두
    # 충청북도다 — 인접 obsid 3900/3902/3903도 모두 충청북도). 정오표로 보고
    # 충청북도로 바로잡았다.
    goesan = MOUNTAIN_STATIONS["3901"]
    assert goesan.mountain_name == "괴산 대곡산"
    assert goesan.region_name == "충청북도"


def test_mountain_stations_goesan_prefixed_entries_are_all_chungcheongbuk():
    # 괴산군은 충청북도 소속이므로, "괴산 ..." 관측소는 예외 없이 전부
    # region_name이 충청북도여야 한다(obsid 3901의 정오표 수정이 다시
    # 깨지지 않도록 하는 회귀 방지 테스트).
    #
    # 이 검사를 "같은 시/군 접두사는 항상 같은 지역명" 같은 일반 규칙으로
    # 넓히지 않는다 — 고성(강원도/경상남도), 군위(경상북도/대구광역시)처럼
    # 실제로 두 광역자치단체에 동명 시/군이 있는 정당한 예외가 있다.
    goesan_stations = [
        station
        for station in MOUNTAIN_STATIONS.values()
        if station.mountain_name.startswith("괴산")
    ]
    assert len(goesan_stations) == 5
    assert all(station.region_name == "충청북도" for station in goesan_stations)


def test_mountain_stations_public_accessor_returns_all_stations_sorted():
    stations = mountain_stations()

    assert len(stations) == len(MOUNTAIN_STATIONS)
    assert all(isinstance(station, MountainStation) for station in stations)
    obs_ids = [int(station.obs_id) for station in stations]
    assert obs_ids == sorted(obs_ids)


def test_mountain_stations_public_accessor_values_match_internal_table():
    gwanaksan = next(s for s in mountain_stations() if s.obs_id == "1917")

    ref = MOUNTAIN_STATIONS["1917"]
    assert gwanaksan.region_name == ref.region_name
    assert gwanaksan.mountain_name == ref.mountain_name
    assert gwanaksan.latitude == ref.latitude
    assert gwanaksan.longitude == ref.longitude
    assert gwanaksan.elevation == ref.elevation
