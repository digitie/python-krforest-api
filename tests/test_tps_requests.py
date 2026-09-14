"""파일 사전 조회와 재시도가 같은 TPS 예산을 사용하는지 검증한다."""

from unittest.mock import AsyncMock

import httpx

from krforest import ForestClient
from krforest.catalog import file_dataset
from krforest.client import _forest_go_request_with_retry

from .conftest import FakeResponse


async def test_file_detail_and_download_each_take_token(fake_client_factory, monkeypatch):
    client, session = fake_client_factory(
        FakeResponse(text='{"contentUrl":"https://www.data.go.kr/cmm/cmm/fileDownload.do"}'),
        FakeResponse(content=b"csv"),
    )
    acquire = AsyncMock(wraps=client._http._rate_limiter.acquire)
    monkeypatch.setattr(client._http._rate_limiter, "acquire", acquire)
    original_get = session.get

    async def get(*args, **kwargs):
        assert acquire.await_count == len(session.calls) + 1
        return await original_get(*args, **kwargs)

    monkeypatch.setattr(session, "get", get)
    assert await client.files.download("15112801") == b"csv"
    assert acquire.await_count == 2


async def test_forest_popup_history_and_download_each_take_token(fake_client_factory, monkeypatch):
    client, session = fake_client_factory(
        FakeResponse(text="popup"), FakeResponse(text="ok"), FakeResponse(content=b"zip")
    )
    acquire = AsyncMock(wraps=client._http._rate_limiter.acquire)
    monkeypatch.setattr(client._http._rate_limiter, "acquire", acquire)
    assert await client.files.download("PBD0000220") == b"zip"
    assert len(session.calls) == acquire.await_count == 3


async def test_each_forest_popup_retry_takes_token(fake_client_factory):
    client, _ = fake_client_factory()
    acquire = AsyncMock(wraps=client._http._rate_limiter.acquire)
    client._http._rate_limiter.acquire = acquire
    request = AsyncMock(
        side_effect=[httpx.ConnectError("offline failure"), FakeResponse(text="ok")]
    )
    response = await _forest_go_request_with_retry(
        request,
        dataset=file_dataset("PBD0000220"),
        endpoint="test-popup",
        rate_limiter=client._http._rate_limiter,
        backoff=0,
    )
    assert response.text == "ok"
    assert request.await_count == acquire.await_count == 2


async def test_file_detail_redirect_takes_another_token(monkeypatch):
    acquisitions = []

    async def handler(request):
        acquisitions.append(acquire.await_count)
        if len(acquisitions) == 1:
            return httpx.Response(302, headers={"location": "/redirected-detail"})
        return httpx.Response(200, text='{"contentUrl":"https://www.data.go.kr/file"}')

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as session:
        client = ForestClient(api_key="TEST_KEY", session=session, max_rps=1000)
        acquire = AsyncMock(wraps=client._http._rate_limiter.acquire)
        monkeypatch.setattr(client._http._rate_limiter, "acquire", acquire)
        assert await client.files.download_url("15112801") == "https://www.data.go.kr/file"
    assert acquisitions == [1, 2]
