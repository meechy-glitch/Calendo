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


def test_forgot_password_unknown_email(client):
    r = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "reset link" in r.json()["message"]


def test_forgot_password_known_email(client, registered_user):
    r = client.post("/auth/forgot-password", json={"email": registered_user["email"]})
    assert r.status_code == 200
    assert "reset link" in r.json()["message"]


def test_reset_password_invalid_token(client):
    r = client.post("/auth/reset-password", json={"token": "badtoken", "new_password": "newpassword123"})
    assert r.status_code == 400
    assert "Invalid" in r.json()["detail"]


def test_reset_password_success(client, registered_user):
    forgot = client.post("/auth/forgot-password", json={"email": registered_user["email"]})
    assert forgot.status_code == 200

    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        row = conn.execute(text("SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1")).fetchone()
    token = row[0]

    r = client.post("/auth/reset-password", json={"token": token, "new_password": "brandnewpass1"})
    assert r.status_code == 200
    assert "updated" in r.json()["message"]

    login = client.post("/auth/login", json={"email": registered_user["email"], "password": "brandnewpass1"})
    assert login.status_code == 200


def test_reset_password_token_already_used(client, registered_user):
    client.post("/auth/forgot-password", json={"email": registered_user["email"]})

    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        row = conn.execute(text("SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1")).fetchone()
    token = row[0]

    client.post("/auth/reset-password", json={"token": token, "new_password": "firstnewpass1"})
    r = client.post("/auth/reset-password", json={"token": token, "new_password": "secondnewpass1"})
    assert r.status_code == 400
    assert "already been used" in r.json()["detail"]


def test_reset_password_expired_token(client, registered_user):
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})

    client.post("/auth/forgot-password", json={"email": registered_user["email"]})
    with engine.connect() as conn:
        row = conn.execute(text("SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1")).fetchone()
        token = row[0]
        past = (datetime.utcnow() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(text(f"UPDATE password_reset_tokens SET expires_at = '{past}' WHERE token = '{token}'"))
        conn.commit()

    r = client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword123"})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"]


def test_reset_password_short_password(client, registered_user):
    client.post("/auth/forgot-password", json={"email": registered_user["email"]})

    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        row = conn.execute(text("SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1")).fetchone()
    token = row[0]

    r = client.post("/auth/reset-password", json={"token": token, "new_password": "short"})
    assert r.status_code == 422
