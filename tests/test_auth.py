def test_register_success(client):
    r = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client, registered_user):
    r = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


def test_register_missing_password(client):
    r = client.post("/auth/register", json={"email": "no-pass@example.com"})
    assert r.status_code == 422


def test_register_missing_email(client):
    r = client.post("/auth/register", json={"password": "password123"})
    assert r.status_code == 422


def test_login_success(client, registered_user):
    r = client.post("/auth/login", json=registered_user)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


def test_login_wrong_password(client, registered_user):
    r = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_nonexistent_email(client):
    r = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert r.status_code == 401


def test_login_missing_fields(client):
    r = client.post("/auth/login", json={"email": "test@example.com"})
    assert r.status_code == 422


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
