from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.conftest import STRONG_PASSWORD, csrf, login, signup


async def test_signup_creates_workspace_and_signs_in(client: httpx.AsyncClient) -> None:
    res = await signup(client)
    body = res.json()
    assert body["user"]["role"] == "owner"
    assert body["user"]["last_login_at"] is not None
    assert body["tenant"]["slug"] == "acme-inc"
    assert body["csrf_token"] == client.cookies.get("sc_csrf")
    assert "password_hash" not in body["user"]
    assert res.headers["Cache-Control"] == "no-store"
    set_cookie = ",".join(res.headers.get_list("set-cookie"))
    assert "sc_access=" in set_cookie and "HttpOnly" in set_cookie
    assert "Path=/v1/auth" in set_cookie  # refresh cookie scoped

    me = await client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@acme.com"


async def test_signup_normalises_email_and_rejects_duplicates(
    client: httpx.AsyncClient,
) -> None:
    await signup(client, email="Owner@ACME.com")
    res = await client.post(
        "/v1/auth/signup",
        json={
            "company_name": "Acme",
            "full_name": "X",
            "email": "owner@acme.com",
            "password": STRONG_PASSWORD,
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "email_taken"


async def test_signup_duplicate_company_gets_unique_slug(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    a = await signup(client_factory(), email="a@x.com", company="Acme")
    b = await signup(client_factory(), email="b@x.com", company="Acme")
    assert a.json()["tenant"]["slug"] == "acme"
    assert b.json()["tenant"]["slug"].startswith("acme-")


@pytest.mark.parametrize("password", ["short", "password1234", "aaaaaaaaaaaaaa", "xxownerxx1234"])
async def test_signup_rejects_weak_passwords(client: httpx.AsyncClient, password: str) -> None:
    res = await client.post(
        "/v1/auth/signup",
        json={
            "company_name": "Acme",
            "full_name": "O",
            "email": "owner@acme.com",
            "password": password,
        },
    )
    assert res.status_code == 422


@pytest.mark.parametrize("settings_overrides", [{"allow_self_signup": False}])
async def test_signup_can_be_disabled(
    client: httpx.AsyncClient, settings_overrides: dict[str, Any]
) -> None:
    res = await client.post(
        "/v1/auth/signup",
        json={
            "company_name": "Acme",
            "full_name": "O",
            "email": "o@acme.com",
            "password": STRONG_PASSWORD,
        },
    )
    assert res.status_code == 403


async def test_login_success_and_generic_failures(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    await signup(client_factory())
    c = client_factory()
    ok = await login(c, "OWNER@acme.com")
    assert ok.status_code == 200
    assert (await c.get("/v1/auth/me")).status_code == 200

    wrong = await login(client_factory(), "owner@acme.com", "not the right password")
    unknown = await login(client_factory(), "nobody@acme.com", "not the right password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # no account enumeration


async def test_lockout_after_repeated_failures(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    await signup(client_factory())
    c = client_factory()
    for _ in range(3):  # max_failed_logins=3 in tests
        assert (await login(c, "owner@acme.com", "wrong password here")).status_code == 401
    locked = await login(c, "owner@acme.com")
    assert locked.status_code == 423
    assert locked.json()["detail"]["code"] == "account_locked"


@pytest.mark.parametrize("settings_overrides", [{"login_rate_limit_per_minute": 2}])
async def test_login_rate_limited(
    client: httpx.AsyncClient, settings_overrides: dict[str, Any]
) -> None:
    for _ in range(2):
        assert (await login(client, "x@acme.com", "whatever password")).status_code == 401
    res = await login(client, "x@acme.com", "whatever password")
    assert res.status_code == 429
    assert res.headers["Retry-After"] == "60"


async def test_unauthenticated_requests_rejected(client: httpx.AsyncClient) -> None:
    assert (await client.get("/v1/auth/me")).status_code == 401
    client.cookies.set("sc_access", "garbage")
    assert (await client.get("/v1/auth/me")).status_code == 401
    bad_bearer = await client.get("/v1/auth/me", headers={"Authorization": "Bearer nope"})
    assert bad_bearer.status_code == 401


async def test_cookie_auth_requires_csrf_on_unsafe_methods(client: httpx.AsyncClient) -> None:
    await signup(client)
    no_csrf = await client.post("/v1/auth/logout-all")
    assert no_csrf.status_code == 403
    wrong = await client.post("/v1/auth/logout-all", headers={"X-CSRF-Token": "forged"})
    assert wrong.status_code == 403
    ok = await client.post("/v1/auth/logout-all", headers=csrf(client))
    assert ok.status_code == 204


async def test_bearer_auth_skips_csrf(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    c = client_factory()
    await signup(c)
    token = c.cookies.get("sc_access")
    api = client_factory()
    headers = {"Authorization": f"Bearer {token}"}
    assert (await api.get("/v1/auth/me", headers=headers)).status_code == 200
    assert (await api.post("/v1/auth/logout-all", headers=headers)).status_code == 204


async def test_refresh_rotates_tokens(client: httpx.AsyncClient) -> None:
    await signup(client)
    old_refresh = client.cookies.get("sc_refresh", path="/v1/auth")
    res = await client.post("/v1/auth/refresh", headers=csrf(client))
    assert res.status_code == 200, res.text
    assert client.cookies.get("sc_refresh", path="/v1/auth") != old_refresh
    assert (await client.get("/v1/auth/me")).status_code == 200


async def test_refresh_requires_csrf_and_cookie(client: httpx.AsyncClient) -> None:
    await signup(client)
    assert (await client.post("/v1/auth/refresh")).status_code == 403
    client.cookies.delete("sc_refresh", path="/v1/auth")
    res = await client.post("/v1/auth/refresh", headers=csrf(client))
    assert res.status_code == 401


async def test_refresh_token_reuse_revokes_session(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    victim = client_factory()
    await signup(victim)
    stolen = victim.cookies.get("sc_refresh", path="/v1/auth")
    assert (await victim.post("/v1/auth/refresh", headers=csrf(victim))).status_code == 200

    attacker = client_factory()
    attacker.cookies.set("sc_refresh", stolen or "", path="/v1/auth")
    attacker.cookies.set("sc_csrf", "x")
    res = await attacker.post("/v1/auth/refresh", headers={"X-CSRF-Token": "x"})
    assert res.status_code == 401
    # Whole session is dead, including the legitimate user's fresh tokens.
    assert (await victim.get("/v1/auth/me")).status_code == 401
    assert (await victim.post("/v1/auth/refresh", headers=csrf(victim))).status_code == 401


@pytest.mark.parametrize("settings_overrides", [{"refresh_reuse_grace_seconds": 60}])
async def test_concurrent_refresh_within_grace_is_not_theft(
    client_factory: Callable[[], httpx.AsyncClient], settings_overrides: dict[str, Any]
) -> None:
    tab1 = client_factory()
    await signup(tab1)
    old = tab1.cookies.get("sc_refresh", path="/v1/auth")
    assert (await tab1.post("/v1/auth/refresh", headers=csrf(tab1))).status_code == 200
    tab2 = client_factory()
    tab2.cookies.set("sc_refresh", old or "", path="/v1/auth")
    tab2.cookies.set("sc_csrf", "x")
    res = await tab2.post("/v1/auth/refresh", headers={"X-CSRF-Token": "x"})
    assert res.status_code == 409
    assert (await tab1.get("/v1/auth/me")).status_code == 200


async def test_logout_revokes_access_token_immediately(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    c = client_factory()
    await signup(c)
    token = c.cookies.get("sc_access")
    assert (await c.post("/v1/auth/logout", headers=csrf(c))).status_code == 204
    assert c.cookies.get("sc_access") is None
    replay = client_factory()
    res = await replay.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_logout_without_session_still_clears(client: httpx.AsyncClient) -> None:
    assert (await client.post("/v1/auth/logout")).status_code == 204


async def test_change_password_revokes_other_sessions(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    laptop = client_factory()
    await signup(laptop)
    phone = client_factory()
    assert (await login(phone, "owner@acme.com")).status_code == 200

    new_pw = "a brand new long passphrase"
    bad = await laptop.post(
        "/v1/auth/change-password",
        headers=csrf(laptop),
        json={"current_password": "wrong one entirely", "new_password": new_pw},
    )
    assert bad.status_code == 400
    same = await laptop.post(
        "/v1/auth/change-password",
        headers=csrf(laptop),
        json={"current_password": STRONG_PASSWORD, "new_password": STRONG_PASSWORD},
    )
    assert same.status_code == 422
    ok = await laptop.post(
        "/v1/auth/change-password",
        headers=csrf(laptop),
        json={"current_password": STRONG_PASSWORD, "new_password": new_pw},
    )
    assert ok.status_code == 204
    assert (await laptop.get("/v1/auth/me")).status_code == 200
    assert (await phone.get("/v1/auth/me")).status_code == 401
    assert (await login(client_factory(), "owner@acme.com", new_pw)).status_code == 200


async def test_list_and_revoke_sessions(
    client_factory: Callable[[], httpx.AsyncClient],
) -> None:
    laptop = client_factory()
    await signup(laptop)
    phone = client_factory()
    await login(phone, "owner@acme.com")

    sessions = (await laptop.get("/v1/auth/sessions")).json()
    assert len(sessions) == 2
    assert sum(s["current"] for s in sessions) == 1
    other = next(s for s in sessions if not s["current"])
    res = await laptop.delete(f"/v1/auth/sessions/{other['id']}", headers=csrf(laptop))
    assert res.status_code == 204
    assert (await phone.get("/v1/auth/me")).status_code == 401
    missing = await laptop.delete(f"/v1/auth/sessions/{other['id'][:-4]}0000", headers=csrf(laptop))
    assert missing.status_code == 404
