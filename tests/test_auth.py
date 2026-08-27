def test_register_success(client):
    r = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123", "name": "Ada Lovelace"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "Ada Lovelace"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_strips_surrounding_whitespace_from_name(client):
    r = client.post(
        "/auth/register",
        json={"email": "spaced@example.com", "password": "password123", "name": "  Grace Hopper  "},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Grace Hopper"


def test_register_duplicate_email(client, registered_user):
    r = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123", "name": "Someone Else"},
    )
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


def test_register_missing_password(client):
    r = client.post("/auth/register", json={"email": "no-pass@example.com", "name": "No Pass"})
    assert r.status_code == 422
    assert "Password is required" in r.json()["detail"]


def test_register_short_password(client):
    r = client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "short", "name": "Shorty McShort"},
    )
    assert r.status_code == 422
    assert "Password must be at least 8 characters" in r.json()["detail"]


def test_register_missing_email(client):
    r = client.post("/auth/register", json={"password": "password123", "name": "No Email"})
    assert r.status_code == 422
    assert "Email is required" in r.json()["detail"]


def test_register_invalid_email(client):
    r = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "password123", "name": "Bad Email"},
    )
    assert r.status_code == 422
    assert "valid email address" in r.json()["detail"]


def test_register_missing_name(client):
    r = client.post("/auth/register", json={"email": "no-name@example.com", "password": "password123"})
    assert r.status_code == 422
    assert "Name is required" in r.json()["detail"]


def test_register_blank_name(client):
    r = client.post(
        "/auth/register",
        json={"email": "blank@example.com", "password": "password123", "name": "   "},
    )
    assert r.status_code == 422
    assert "Name is required" in r.json()["detail"]


def test_register_name_too_short(client):
    r = client.post(
        "/auth/register",
        json={"email": "tiny@example.com", "password": "password123", "name": "A"},
    )
    assert r.status_code == 422
    assert "Name must be at least 2 characters" in r.json()["detail"]


def test_register_name_too_long(client):
    r = client.post(
        "/auth/register",
        json={"email": "long@example.com", "password": "password123", "name": "A" * 101},
    )
    assert r.status_code == 422
    assert "100 characters or less" in r.json()["detail"]


def test_me_returns_id_email_and_name(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert isinstance(data["id"], int)


def test_me_name_is_null_for_accounts_created_without_one(client):
    # The demo account predates the name field and is seeded without one.
    token = client.post("/auth/demo").json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["name"] is None


def test_patch_me_updates_name(client, auth_headers):
    r = client.patch("/auth/me", json={"name": "  Renamed User  "}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed User"

    again = client.get("/auth/me", headers=auth_headers)
    assert again.json()["name"] == "Renamed User"


def test_patch_me_rejects_blank_name(client, auth_headers):
    r = client.patch("/auth/me", json={"name": "   "}, headers=auth_headers)
    assert r.status_code == 422
    assert "Name is required" in r.json()["detail"]

    unchanged = client.get("/auth/me", headers=auth_headers)
    assert unchanged.json()["name"] == "Test User"


def test_patch_me_requires_auth(client):
    r = client.patch("/auth/me", json={"name": "Nobody"})
    assert r.status_code in (401, 403)


def test_patch_me_only_touches_the_caller(client, auth_headers):
    other = client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "password123", "name": "Other User"},
    )
    other_id = other.json()["id"]

    # Even with another user's id in the body, the write is scoped to the token.
    r = client.patch(
        "/auth/me",
        json={"id": other_id, "name": "Hijacked"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Hijacked"
    assert r.json()["id"] != other_id

    other_token = client.post(
        "/auth/login", json={"email": "other@example.com", "password": "password123"}
    ).json()["access_token"]
    other_me = client.get("/auth/me", headers={"Authorization": f"Bearer {other_token}"})
    assert other_me.json()["name"] == "Other User"


def test_patch_me_cannot_change_email(client, auth_headers):
    r = client.patch(
        "/auth/me",
        json={"email": "hacked@example.com", "name": "Still Me"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


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
