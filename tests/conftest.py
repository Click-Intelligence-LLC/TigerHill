import asyncio
import os
from typing import Iterator

import httpx
import pytest


class SyncASGIClient:
    def __init__(self, app):
        transport = httpx.ASGITransport(app=app)
        self._client = httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        )

    def request(self, method: str, url: str, **kwargs):
        return asyncio.run(self._client.request(method, url, **kwargs))

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def close(self):
        asyncio.run(self._client.aclose())


@pytest.fixture()
def api_client(tmp_path) -> Iterator[SyncASGIClient]:
    """
    Provide a synchronous client backed by HTTPX ASGI transport.
    """
    db_path = tmp_path / "api_test.db"
    os.environ["TIGERHILL_DB_PATH"] = str(db_path)

    import backend.database as database

    database.set_db_path(str(db_path))
    asyncio.run(database.init_db())

    from backend.main import app

    client = SyncASGIClient(app)
    try:
        yield client
    finally:
        client.close()
