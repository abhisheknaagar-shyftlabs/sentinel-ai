async def test_root_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


async def test_versioned_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
