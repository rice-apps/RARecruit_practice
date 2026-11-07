"""Tests for login.py. Run with: .venv/bin/pytest -q

Google is mocked, so these run offline and never use real accounts.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

import login


@pytest.fixture
def client():
    return TestClient(login.app, base_url="http://localhost:8080")


def start_login(client):
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 307
    return urlparse(resp.headers["location"])


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["logged_in"] is False


def test_me_requires_login(client):
    assert client.get("/me").status_code == 401


def test_login_redirects_to_google(client):
    url = start_login(client)
    params = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert params["redirect_uri"] == [login.REDIRECT_URI]
    assert "openid" in params["scope"][0]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"][0]


def test_callback_rejects_wrong_state(client):
    start_login(client)
    resp = client.get("/oauth2callback?state=forged&code=abc")
    assert resp.status_code == 400


def test_callback_without_login_is_rejected(client):
    resp = client.get("/oauth2callback?state=anything&code=abc")
    assert resp.status_code == 400


def test_callback_reports_google_error(client):
    resp = client.get("/oauth2callback?error=access_denied")
    assert resp.status_code == 400
    assert "access_denied" in resp.json()["detail"]


def test_full_login_and_logout(client, monkeypatch):
    class FakeCreds:
        id_token = "fake.jwt.token"

    def fake_fetch_token(self, **kwargs):
        assert "code=abc" in kwargs["authorization_response"]

    monkeypatch.setattr(login.google_auth_oauthlib.flow.Flow, "fetch_token", fake_fetch_token)
    monkeypatch.setattr(
        login.google_auth_oauthlib.flow.Flow, "credentials", property(lambda self: FakeCreds())
    )
    monkeypatch.setattr(
        login.id_token,
        "verify_oauth2_token",
        lambda token, req, audience: {
            "sub": "123",
            "email": "student@rice.edu",
            "email_verified": True,
            "name": "Test Student",
            "picture": None,
        },
    )

    state = parse_qs(start_login(client).query)["state"][0]
    resp = client.get(f"/oauth2callback?state={state}&code=abc")
    assert resp.status_code == 200  # followed redirect to /me
    assert resp.json()["email"] == "student@rice.edu"
    assert client.get("/").json()["logged_in"] is True

    # The same state can't be replayed.
    assert client.get(f"/oauth2callback?state={state}&code=abc").status_code == 400

    client.get("/logout")
    assert client.get("/me").status_code == 401
