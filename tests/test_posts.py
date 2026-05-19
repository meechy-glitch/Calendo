POST_DATA = {
    "title": "Test Post",
    "caption": "A test caption",
    "platform": "instagram",
    "scheduled_date": "2025-05-15",
    "status": "draft",
}


def test_create_post(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test Post"
    assert data["platform"] == "instagram"
    assert data["status"] == "draft"
    assert "id" in data


def test_create_post_unauthenticated(client):
    r = client.post("/posts", json=POST_DATA)
    assert r.status_code == 403


def test_list_posts(client, auth_headers):
    client.post("/posts", json=POST_DATA, headers=auth_headers)
    r = client.get("/posts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_posts_month_filter_match(client, auth_headers):
    client.post("/posts", json=POST_DATA, headers=auth_headers)
    r = client.get("/posts?month=2025-05", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_posts_month_filter_no_match(client, auth_headers):
    client.post("/posts", json=POST_DATA, headers=auth_headers)
    r = client.get("/posts?month=2025-06", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 0


def test_get_post(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]
    r = client.get(f"/posts/{post_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == post_id


def test_update_post_status(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]
    r = client.put(
        f"/posts/{post_id}", json={"status": "published"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"


def test_update_post_partial(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]
    r = client.put(
        f"/posts/{post_id}", json={"title": "Updated Title"}, headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated Title"
    assert data["platform"] == "instagram"  # unchanged


def test_delete_post(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]
    r = client.delete(f"/posts/{post_id}", headers=auth_headers)
    assert r.status_code == 204
    r2 = client.get(f"/posts/{post_id}", headers=auth_headers)
    assert r2.status_code == 404


def test_get_post_404(client, auth_headers):
    r = client.get("/posts/99999", headers=auth_headers)
    assert r.status_code == 404


def test_post_wrong_user_put_forbidden(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]

    client.post(
        "/auth/register",
        json={"email": "user2@example.com", "password": "password123"},
    )
    login_r = client.post(
        "/auth/login",
        json={"email": "user2@example.com", "password": "password123"},
    )
    user2_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

    r = client.put(
        f"/posts/{post_id}", json={"status": "published"}, headers=user2_headers
    )
    assert r.status_code in [403, 404]


def test_post_wrong_user_delete_forbidden(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]

    client.post(
        "/auth/register",
        json={"email": "user3@example.com", "password": "password123"},
    )
    login_r = client.post(
        "/auth/login",
        json={"email": "user3@example.com", "password": "password123"},
    )
    user3_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

    r = client.delete(f"/posts/{post_id}", headers=user3_headers)
    assert r.status_code in [403, 404]


def test_update_published_post_blocked(client, auth_headers):
    create_r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = create_r.json()["id"]
    client.put(f"/posts/{post_id}", json={"status": "published"}, headers=auth_headers)
    r = client.put(
        f"/posts/{post_id}", json={"title": "Attempt to Edit"}, headers=auth_headers
    )
    assert r.status_code == 403
    assert "cannot be edited" in r.json()["detail"]


def test_csv_export(client, auth_headers):
    client.post("/posts", json=POST_DATA, headers=auth_headers)
    r = client.get("/posts/export/csv?month=2025-05", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    content = r.content.decode()
    assert "Title" in content
    assert "Test Post" in content
    assert "instagram" in content


def test_csv_export_empty(client, auth_headers):
    r = client.get("/posts/export/csv?month=2025-01", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    content = r.content.decode()
    assert "Title" in content
