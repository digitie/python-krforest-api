"""원격 응답 레코드를 공개 Pydantic 모델로 파싱하는 함수."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from ._convert import extract_address, extract_coordinate, to_float_or_none
from ._mountain_stations import MOUNTAIN_STATIONS
from .models import (
    ErosionControlDam,
    ForestDustMeasurement,
    ForestDustStation,
    LandslideForecastIssue,
    MountainWeather,
    RecreationForestReservation,
    StandardRecreationForest,
    WildfireRiskForecast,
)

KST = timezone(timedelta(hours=9))
WildfireScope = Literal["national", "sido", "sigungu"]

_INSTITUTION_ID_KEYS = (
    "institution_id",
    "insttId",
    "insttid",
    "기관ID",
    "기관아이디",
    "기관코드",
    "휴양림ID",
)
_INSTITUTION_NAME_KEYS = (
    "institution_name",
    "insttNm",
    "insttnm",
    "기관명",
    "휴양림명",
    "자연휴양림명",
    "명칭",
)
_GOODS_NAME_KEYS = ("goodsNm", "goodsnm", "상품명", "객실명", "시설명")
_STAY_DATE_KEYS = ("stngDt", "stngdt", "숙박일자", "이용일자")
_STATUS_KEYS = ("status", "상태", "예약상태")


def parse_mountain_weather(row: dict[str, Any]) -> MountainWeather:
    """산악기상 원본 레코드를 typed 관측 모델로 파싱한다.

    ``mountListSearch`` 응답 자체는 좌표·고도·지역명을 담지 않으므로,
    ``obs_id``로 :data:`krforest._mountain_stations.MOUNTAIN_STATIONS` 정적
    참조 테이블을 조회해 채운다. 응답에 좌표 필드가 실제로 포함된 경우(향후
    provider 변경 등)에는 그 값을 우선한다.
    """

    key_map = _lower_key_map(row)
    obs_id = first_text(row, "obsid", "obsId", "obs_id", "관측소ID", key_map=key_map)
    station = MOUNTAIN_STATIONS.get(obs_id) if obs_id else None
    latitude, longitude = extract_coordinate(row)
    if latitude is None and longitude is None and station is not None:
        latitude, longitude = station.latitude, station.longitude
    obs_name = first_text(row, "obsname", "obsName", "obs_name", "관측소명", key_map=key_map)
    return MountainWeather(
        obs_id=obs_id,
        obs_name=obs_name or (station.mountain_name if station else None),
        local_area=first_text(row, "localarea", "localArea", "local_area", "지역", key_map=key_map),
        region_name=station.region_name if station else None,
        elevation=station.elevation if station else None,
        observed_at=parse_datetime(
            first_text(row, "tm", "observedAt", "관측시간", key_map=key_map)
        ),
        temperature_10m=_first_float(row, "tm10m", "temperature10m", "기온10m", key_map=key_map),
        temperature_2m=_first_float(row, "tm2m", "temperature2m", "기온2m", key_map=key_map),
        humidity_10m=_first_float(row, "hm10m", "humidity10m", "습도10m", key_map=key_map),
        humidity_2m=_first_float(row, "hm2m", "humidity2m", "습도2m", key_map=key_map),
        pressure=_first_float(row, "pa", "pressure", "기압", key_map=key_map),
        rainfall_tipping=_first_float(
            row, "rn", "rainfallTipping", "전도식강우량", key_map=key_map
        ),
        rainfall_weight=_first_float(
            row, "cprn", "rainfallWeight", "무게식강우량", key_map=key_map
        ),
        ground_temperature=_first_float(
            row, "ts", "groundTemperature", "지면온도", key_map=key_map
        ),
        wind_direction_10m=_first_float(
            row, "wd10m", "windDirection10m", "풍향10m", key_map=key_map
        ),
        wind_direction_10m_name=_none_if_dash(
            first_text(row, "wd10mstr", "windDirection10mName", "풍향10m문자", key_map=key_map)
        ),
        wind_direction_2m=_first_float(row, "wd2m", "windDirection2m", "풍향2m", key_map=key_map),
        wind_direction_2m_name=_none_if_dash(
            first_text(row, "wd2mstr", "windDirection2mName", "풍향2m문자", key_map=key_map)
        ),
        wind_speed_10m=_first_float(row, "ws10m", "windSpeed10m", "풍속10m", key_map=key_map),
        wind_speed_2m=_first_float(row, "ws2m", "windSpeed2m", "풍속2m", key_map=key_map),
        latitude=latitude,
        longitude=longitude,
        raw=row,
    )


def parse_wildfire_risk_forecast(
    row: dict[str, Any], *, scope: WildfireScope = "national"
) -> WildfireRiskForecast:
    """산불위험지수 V2 전국·시도·시군구 row를 typed 모델로 파싱한다."""

    if scope not in {"national", "sido", "sigungu"}:
        raise ValueError(f"unsupported wildfire risk scope: {scope!r}")
    key_map = _lower_key_map(row)
    if scope == "sigungu":
        region_code = first_text(
            row,
            "sigucode",
            "sigunguCode",
            "시군구코드",
            "regioncode",
            "regionCode",
            "지역코드",
            key_map=key_map,
        )
        region_name = first_text(
            row,
            "sigun",
            "sigunguName",
            "regionName",
            "시군구명",
            "doname",
            "시도명",
            key_map=key_map,
        )
    else:
        region_code = first_text(
            row, "regioncode", "regionCode", "지역코드", "sigucode", key_map=key_map
        )
        region_name = first_text(
            row, "doname", "regionName", "시도명", "sigun", "시군구명", key_map=key_map
        )
    return WildfireRiskForecast(
        scope=scope,
        analysis_at=parse_datetime(
            first_text(row, "analdate", "analysisAt", "분석일시", key_map=key_map)
        ),
        area=first_text(row, "area", "areaName", "지역", key_map=key_map),
        region_code=region_code,
        region_name=region_name,
        upper_region_code=first_text(
            row, "upplocalcd", "upperRegionCode", "상위지역코드", key_map=key_map
        ),
        d1=_first_float(row, "d1", key_map=key_map),
        d2=_first_float(row, "d2", key_map=key_map),
        d3=_first_float(row, "d3", key_map=key_map),
        d4=_first_float(row, "d4", key_map=key_map),
        maximum=_first_float(row, "maxi", "maximum", "max", key_map=key_map),
        mean_average=_first_float(row, "meanavg", "meanAverage", "평균", key_map=key_map),
        minimum=_first_float(row, "mini", "minimum", "min", key_map=key_map),
        standard_deviation=_first_float(
            row, "std", "standardDeviation", "표준편차", key_map=key_map
        ),
        raw=row,
    )


def parse_forest_dust_measurement(row: dict[str, Any]) -> ForestDustMeasurement:
    """청정넷(AICAN) 측정데이터 row를 typed 모델로 파싱한다."""

    key_map = _lower_key_map(row)
    return ForestDustMeasurement(
        station_code=first_text(row, "obsrr_tpcd", key_map=key_map),
        observed_at=parse_datetime(first_text(row, "obsrt_dtm", key_map=key_map)),
        temperature=_first_float(row, "obsrt_tmprt", key_map=key_map),
        humidity=_first_float(row, "obsrt_hmdt", key_map=key_map),
        wind_direction=_first_float(row, "obsrt_wndrc_val", key_map=key_map),
        wind_speed=_first_float(row, "obsrt_ws", key_map=key_map),
        pm10=_first_float(row, "obsrt_pm10_val", key_map=key_map),
        pm25=_first_float(row, "obsrt_pm25_val", key_map=key_map),
        pm01=_first_float(row, "obsrt_pm01_val", key_map=key_map),
        avoc_pm10=_first_float(row, "avoc_obsrt_pm10_val", key_map=key_map),
        avoc_pm25=_first_float(row, "avoc_obsrt_pm25_val", key_map=key_map),
        avoc_pm01=_first_float(row, "avoc_obsrt_pm01_val", key_map=key_map),
        raw=row,
    )


def parse_forest_dust_station(row: dict[str, Any]) -> ForestDustStation:
    """청정넷(AICAN) 운영현황(관측소 속성) row를 typed 모델로 파싱한다."""

    latitude, longitude = extract_coordinate(
        row,
        extra_latitude_keys=("obsrr_lttd",),
        extra_longitude_keys=("obsrr_lngtd",),
    )
    address = extract_address(row, extra_keys=("obsrr_addr",))
    key_map = _lower_key_map(row)
    return ForestDustStation(
        station_name=first_text(row, "obsrr_nm", key_map=key_map),
        station_code=first_text(row, "obsrr_tpcd", key_map=key_map),
        station_group_code=first_text(row, "obsrr_group_cd", key_map=key_map),
        description=first_text(row, "obsrr_dscrt", key_map=key_map),
        address=address,
        installed_at=first_text(row, "obsrr_instl_dt", key_map=key_map),
        equipment_name=first_text(row, "eqpmn_nm", key_map=key_map),
        equipment_model=first_text(row, "eqpmn_model_nm", key_map=key_map),
        equipment_maker=first_text(row, "eqpmn_mkr_nm", key_map=key_map),
        equipment_reference_number=first_text(row, "obsrr_mdm_no", key_map=key_map),
        elevation=_first_float(row, "obsrr_haslv", key_map=key_map),
        latitude=latitude,
        longitude=longitude,
        raw=row,
    )


def parse_landslide_forecast_issue(row: dict[str, Any]) -> LandslideForecastIssue:
    """산사태 예보발령 API row를 typed 모델로 파싱한다."""

    key_map = _lower_key_map(row)
    return LandslideForecastIssue(
        issue_kind_code=first_text(
            row, "frcstIssuKindCd", "forecastIssueKindCode", key_map=key_map
        ),
        issue_kind_name=first_text(
            row, "frcstIssuKindNm", "forecastIssueKindName", key_map=key_map
        ),
        issuing_institution=first_text(
            row, "ocrnFrcstIssuInsttNm", "issuingInstitution", "발생예보발령기관명", key_map=key_map
        ),
        status=first_text(row, "frcstIssuStts", "status", "예보발령상태", key_map=key_map),
        issued_at=parse_datetime(
            first_text(
                row, "frstFrcstIssuDt", "firstForecastIssueDate", "발령일시", key_map=key_map
            )
        ),
        raw=row,
    )


def parse_erosion_control_dam(row: dict[str, Any]) -> ErosionControlDam:
    """사방댐 원본 레코드를 좌표 포함 모델로 파싱한다."""

    latitude, longitude = extract_coordinate(row)
    return ErosionControlDam(latitude=latitude, longitude=longitude, raw=row)


def parse_recreation_forest_reservation(row: dict[str, Any]) -> RecreationForestReservation:
    """국립자연휴양림 예약정보 레코드를 안정적인 필드로 파싱한다."""

    key_map = _lower_key_map(row)
    return RecreationForestReservation(
        institution_id=first_text(row, *_INSTITUTION_ID_KEYS, key_map=key_map),
        institution_name=first_text(row, *_INSTITUTION_NAME_KEYS, key_map=key_map),
        goods_name=first_text(row, *_GOODS_NAME_KEYS, key_map=key_map),
        stay_date=first_text(row, *_STAY_DATE_KEYS, key_map=key_map),
        status=first_text(row, *_STATUS_KEYS, key_map=key_map),
        raw=row,
    )


def parse_standard_recreation_forest(row: dict[str, Any]) -> StandardRecreationForest:
    """전국휴양림표준데이터 레코드를 주소와 좌표 포함 모델로 파싱한다."""

    latitude, longitude = extract_coordinate(row)
    address = extract_address(row, extra_keys=("소재지도로명주소", "소재지지번주소"))
    key_map = _lower_key_map(row)

    return StandardRecreationForest(
        name=first_text(row, "rcrfrstNm", "휴양림명", key_map=key_map),
        sido_name=first_text(row, "ctprvnNm", "시도명", key_map=key_map),
        forest_type=first_text(row, "rcrfrstType", "휴양림구분", key_map=key_map),
        area=first_text(row, "rcrfrstFcltyAr", "휴양림면적", key_map=key_map),
        capacity=first_text(row, "aceptncCo", "수용인원수", key_map=key_map),
        entrance_fee=first_text(row, "admfee", "입장료", key_map=key_map),
        accommodation_available=first_text(row, "stayngPosblYn", "숙박가능여부", key_map=key_map),
        main_facilities=first_text(row, "mstrFclty", "주요시설명", key_map=key_map),
        address=address,
        management_agency=first_text(row, "institutionNm", "관리기관명", key_map=key_map),
        phone_number=first_text(row, "phoneNumber", "관리기관전화번호", key_map=key_map),
        homepage_url=first_text(row, "homepageUrl", "홈페이지주소", key_map=key_map),
        latitude=latitude,
        longitude=longitude,
        reference_date=first_text(row, "referenceDate", "데이터기준일자", key_map=key_map),
        institution_code=first_text(row, "instt_code", "제공기관코드", key_map=key_map),
        raw=row,
    )


def _lower_key_map(row: Mapping[str, Any]) -> dict[str, str]:
    """row의 키를 소문자 기준으로 한 번만 색인한다."""

    return {str(key).lower(): key for key in row}


def first_text(
    row: Mapping[str, Any], *keys: str, key_map: Mapping[str, str] | None = None
) -> str | None:
    """대소문자 차이를 흡수해 첫 번째 비어 있지 않은 문자열 값을 찾는다."""

    lower_key_map = key_map if key_map is not None else _lower_key_map(row)
    for key in keys:
        value = _strip_or_none(row.get(key))
        if value is not None:
            return value
        actual_key = lower_key_map.get(key.lower())
        if actual_key is None:
            continue
        value = _strip_or_none(row.get(actual_key))
        if value is not None:
            return value
    return None


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _none_if_dash(value: str | None) -> str | None:
    """산악기상(mtweather) 등 일부 provider는 결측값을 문자열 "-"로 반환한다.

    숫자 필드는 ``to_float_or_none``의 ``ValueError`` 처리로 이미 ``None``이
    되지만, 문자열 필드(예: 풍향 방위 문자)는 그대로 "-"가 남으므로 명시적으로
    걸러낸다.
    """

    return None if value == "-" else value


def _first_float(
    row: Mapping[str, Any], *keys: str, key_map: Mapping[str, str] | None = None
) -> float | None:
    value = first_text(row, *keys, key_map=key_map)
    return to_float_or_none(value)


def parse_datetime(value: Any) -> datetime | None:
    """공공 API 날짜 문자열을 KST aware datetime으로 변환한다."""

    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=KST)
    text = _strip_or_none(value)
    if text is None:
        return None
    normalized = text.replace("/", "-").replace("T", " ")
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    if normalized.isdigit():
        # 구분자 없는 숫자열(예: yyyyMMddHHmm)은 길이로 형식을 고정해서만 파싱한다.
        # datetime.fromisoformat()도 strptime의 %H%M%S 등도 자릿수를 넘나들며
        # 잘못 역추적할 수 있어(예: "202511011530"을 15:03으로 오인), 둘 다 거치지
        # 않고 이 분기에서 바로 처리해야 한다.
        digit_format = {
            14: "%Y%m%d%H%M%S",
            12: "%Y%m%d%H%M",
            10: "%Y%m%d%H",
            8: "%Y%m%d",
        }.get(len(normalized))
        if digit_format is None:
            return None
        try:
            digit_parsed = datetime.strptime(normalized, digit_format)
        except ValueError:
            return None
        return digit_parsed.replace(tzinfo=KST)

    parsed: datetime | None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ):
            try:
                parsed = datetime.strptime(normalized, fmt)
            except ValueError:
                continue
            break
    if parsed is None:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=KST)
