"""Tests for the role-based dashboard in main.py. Run with: .venv/bin/pytest -q

MongoDB is replaced with an in-memory fake, so these never touch the real database.
"""

import pytest

import main


class FakeUpdateResult:
    def __init__(self, matched_count):
        self.matched_count = matched_count


class FakeUsers:
    """Just enough of a pymongo collection for main.py."""

    def __init__(self, docs):
        self.docs = docs

    def _matches(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    def find_one(self, query):
        return next((dict(d) for d in self.docs if self._matches(d, query)), None)

    def find(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if self._matches(d, query)]
        if sort:
            rows.sort(key=lambda d: d.get(sort[0][0]) or "")
        if projection:
            keep = [k for k, v in projection.items() if v]
            rows = [{k: d.get(k) for k in keep} for d in rows]
        return rows

    def update_one(self, query, update):
        for d in self.docs:
            if self._matches(d, query):
                d.update(update["$set"])
                return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    def role_of(self, google_id):
        return self.find_one({"google_id": google_id})["role"]


@pytest.fixture
def users(monkeypatch):
    fake = FakeUsers([
        {"google_id": "admin-1", "name": "Ada Admin", "email": "ada@rice.edu", "role": "admin"},
        {"google_id": "app-1", "name": "Sam Student", "email": "sam@rice.edu", "role": "applicant"},
        {"google_id": "app-2", "name": "<script>alert(1)</script>", "email": "x@rice.edu", "role": "applicant"},
    ])
    monkeypatch.setattr(main, "users_collection", fake)
    return fake


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


def log_in(client, google_id):
    with client.session_transaction() as s:
        s["google_id"] = google_id


def admin_token(client):
    client.get("/dashboard")
    with client.session_transaction() as s:
        return s["csrf_token"]


def test_dashboard_requires_login(client, users):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/authorize")


def test_applicant_sees_only_their_role(client, users):
    log_in(client, "app-1")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "role: <b>applicant</b>" in html
    assert "ada@rice.edu" not in html
    assert "<form" not in html


def test_applicant_cannot_change_roles(client, users):
    log_in(client, "app-1")
    with client.session_transaction() as s:
        s["csrf_token"] = "t"
    resp = client.post("/admin/users/app-1/role", data={"role": "admin", "csrf_token": "t"})
    assert resp.status_code == 403
    assert users.role_of("app-1") == "applicant"


def test_admin_sees_all_users(client, users):
    log_in(client, "admin-1")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "sam@rice.edu" in html and "x@rice.edu" in html
    assert html.count("<form") == 2  # everyone except the admin themself
    assert "admin (you)" in html


def test_names_are_html_escaped(client, users):
    log_in(client, "admin-1")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_admin_changes_role(client, users):
    log_in(client, "admin-1")
    token = admin_token(client)
    resp = client.post("/admin/users/app-1/role",
                       data={"role": "admin", "csrf_token": token}, follow_redirects=True)
    assert resp.status_code == 200
    assert "Role updated to admin." in resp.get_data(as_text=True)
    assert users.role_of("app-1") == "admin"


def test_role_change_needs_valid_token(client, users):
    log_in(client, "admin-1")
    admin_token(client)
    resp = client.post("/admin/users/app-1/role", data={"role": "admin", "csrf_token": "wrong"})
    assert resp.status_code == 400
    assert users.role_of("app-1") == "applicant"


def test_rejects_unknown_role(client, users):
    log_in(client, "admin-1")
    token = admin_token(client)
    resp = client.post("/admin/users/app-1/role", data={"role": "superuser", "csrf_token": token})
    assert resp.status_code == 400
    assert users.role_of("app-1") == "applicant"


def test_admin_cannot_demote_self(client, users):
    log_in(client, "admin-1")
    token = admin_token(client)
    resp = client.post("/admin/users/admin-1/role",
                       data={"role": "applicant", "csrf_token": token}, follow_redirects=True)
    assert "can&#39;t change your own role" in resp.get_data(as_text=True)
    assert users.role_of("admin-1") == "admin"


def test_demoted_admin_loses_access_immediately(client, users):
    log_in(client, "admin-1")
    users.update_one({"google_id": "admin-1"}, {"$set": {"role": "applicant"}})
    html = client.get("/dashboard").get_data(as_text=True)
    assert "role: <b>applicant</b>" in html and "<form" not in html


def test_logout_clears_session(client, users):
    log_in(client, "admin-1")
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302
