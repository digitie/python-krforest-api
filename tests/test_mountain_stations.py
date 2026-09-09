from __future__ import annotations

from krforest._mountain_stations import MOUNTAIN_STATIONS


def test_mountain_stations_table_has_expected_size_and_unique_keys():
    assert len(MOUNTAIN_STATIONS) == 454
    assert len(set(MOUNTAIN_STATIONS)) == len(MOUNTAIN_STATIONS)


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
