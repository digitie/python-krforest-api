from __future__ import annotations

import json
from typing import Any

import pytest

from krforest import ForestClient


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        status_code: int = 200,
        text: str | None = None,
        content: bytes | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._json_error = json_error
        self.status_code = status_code
        if text is not None:
            self.text = text
        elif isinstance(payload, str):
            self.text = payload
        else:
            self.text = json.dumps(payload)
        self.content = content if content is not None else self.text.encode()

    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)

    async def aclose(self) -> None:
        return None


def public_payload(
    item: Any,
    *,
    result_code: str = "00",
    result_msg: str = "NORMAL SERVICE.",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int | None = None,
) -> dict[str, Any]:
    items = "" if item is None else {"item": item}
    if total_count is None:
        if isinstance(item, list):
            total_count = len(item)
        elif item is None:
            total_count = 0
        else:
            total_count = 1
    return {
        "response": {
            "header": {"resultCode": result_code, "resultMsg": result_msg},
            "body": {
                "items": items,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
                "totalCount": total_count,
            },
        }
    }


def standard_data_payload(
    item: Any,
    *,
    result_code: str = "00",
    result_msg: str = "NORMAL SERVICE.",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int | None = None,
) -> dict[str, Any]:
    """data.go.kr **표준데이터** gateway의 봉투 — `response` 래퍼가 없다.

    `api.data.go.kr/openapi/tn_pubr_*`는 `header`/`body`를 최상위에 둔다
    (2026-09-19 `tn_pubr_public_rcrfrst_api` 실측). `public_payload`가 **항상**
    래퍼를 씌우므로 그 대역만 쓰는 한 이 형태는 테스트에 나타나지 않는다 —
    실제로 상류가 래퍼를 벗었을 때 prod에서만 깨진 이유다.
    """

    wrapped = public_payload(
        item,
        result_code=result_code,
        result_msg=result_msg,
        page_no=page_no,
        num_of_rows=num_of_rows,
        total_count=total_count,
    )
    return dict(wrapped["response"])


def flat_payload(
    items: Any,
    *,
    result_code: str = "00",
    result_msg: str = "OK",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int | None = None,
) -> dict[str, Any]:
    """청정넷(AICAN) 계열처럼 response.header/body로 감싸지 않는 flat envelope."""

    if total_count is None:
        total_count = len(items) if isinstance(items, list) else (1 if items else 0)
    return {
        "resultCode": result_code,
        "resultMsg": result_msg,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "totalCount": total_count,
        "items": items,
    }


def xml_payload(
    item_xml: str,
    *,
    result_code: str = "00",
    result_msg: str = "NORMAL SERVICE.",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int = 1,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>{result_code}</resultCode>
    <resultMsg>{result_msg}</resultMsg>
  </header>
  <body>
    <items>{item_xml}</items>
    <numOfRows>{num_of_rows}</numOfRows>
    <pageNo>{page_no}</pageNo>
    <totalCount>{total_count}</totalCount>
  </body>
</response>"""


@pytest.fixture
def fake_client_factory() -> Any:
    def factory(*responses: FakeResponse, **kwargs: Any) -> tuple[ForestClient, FakeSession]:
        session = FakeSession(list(responses))
        client = ForestClient(api_key="TEST_KEY", session=session, **kwargs)
        return client, session

    return factory
