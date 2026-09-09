from __future__ import annotations

from krforest.parser import parse_datetime


def test_parse_datetime_yyyymmddhhmm_does_not_corrupt_minutes():
    # 회귀 방지: strptime("%Y%m%d%H%M%S")이 12자리 문자열에서 분(minute) 자리를
    # 초(second)로 잘못 역추적해 "202511011530"을 15:03으로 깨뜨리던 버그.
    parsed = parse_datetime("202511011530")

    assert parsed is not None
    assert (parsed.hour, parsed.minute, parsed.second) == (15, 30, 0)


def test_parse_datetime_handles_all_supported_digit_lengths():
    assert parse_datetime("20260820120000").isoformat() == "2026-08-20T12:00:00+09:00"
    assert parse_datetime("202608201200").isoformat() == "2026-08-20T12:00:00+09:00"
    assert parse_datetime("2026082012").isoformat() == "2026-08-20T12:00:00+09:00"
    assert parse_datetime("20260820").isoformat() == "2026-08-20T00:00:00+09:00"


def test_parse_datetime_handles_separated_formats():
    assert parse_datetime("2026-08-20 12:30:00").isoformat() == "2026-08-20T12:30:00+09:00"
    assert parse_datetime("2026-08-20 12:30").isoformat() == "2026-08-20T12:30:00+09:00"
    assert parse_datetime("2026-08-20").isoformat() == "2026-08-20T00:00:00+09:00"
    assert parse_datetime("2026-08-20T12:30:00Z").isoformat() == "2026-08-20T12:30:00+00:00"


def test_parse_datetime_returns_none_for_blank_or_unparseable():
    assert parse_datetime(None) is None
    assert parse_datetime("") is None
    assert parse_datetime("-") is None
    assert parse_datetime("not-a-date") is None
