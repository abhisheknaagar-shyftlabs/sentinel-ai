async def test_register_login_and_me(client):
    register_payload = {
        "email": "engineer@sentinel.ai",
        "full_name": "Ada Lovelace",
        "password": "supersecret123",
    }
    register_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["success"] is True
    assert register_body["data"]["user"]["email"] == register_payload["email"]
    access_token = register_body["data"]["access_token"]

    duplicate_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "CONFLICT"

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert "access_token" in login_body["data"]

    bad_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": register_payload["email"], "password": "wrong-password"},
    )
    assert bad_login_response.status_code == 401

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == register_payload["email"]

    unauthenticated_response = await client.get("/api/v1/auth/me")
    assert unauthenticated_response.status_code == 401


async def test_refresh_token_flow(client):
    register_payload = {"email": "refresh@sentinel.ai", "password": "supersecret123"}
    register_response = await client.post("/api/v1/auth/register", json=register_payload)
    refresh_token = register_response.json()["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()["data"]

    invalid_refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert invalid_refresh_response.status_code == 401
