from collections.abc import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import STRONG_PASSWORD, csrf, login, signup

Factory = Callable[[], httpx.AsyncClient]


async def _owner(
    factory: Factory, email: str = "owner@acme.com", company: str = "Acme"
) -> httpx.AsyncClient:
    c = factory()
    await signup(c, email=email, company=company)
    return c


async def _add_user(actor: httpx.AsyncClient, email: str, role: str) -> httpx.Response:
    return await actor.post(
        "/v1/users",
        headers=csrf(actor),
        json={
            "email": email,
            "full_name": email.split("@")[0],
            "role": role,
            "password": STRONG_PASSWORD,
        },
    )


async def _signed_in(factory: Factory, email: str) -> httpx.AsyncClient:
    c = factory()
    assert (await login(c, email)).status_code == 200
    return c


async def test_owner_creates_and_lists_users(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    res = await _add_user(owner, "agent@acme.com", "agent")
    assert res.status_code == 201
    users = (await owner.get("/v1/users")).json()
    assert {u["email"] for u in users} == {"owner@acme.com", "agent@acme.com"}


async def test_agent_cannot_manage_users(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    await _add_user(owner, "agent@acme.com", "agent")
    agent = await _signed_in(client_factory, "agent@acme.com")
    assert (await agent.get("/v1/users")).status_code == 403
    assert (await _add_user(agent, "x@acme.com", "agent")).status_code == 403
    assert (await agent.get("/v1/audit-events")).status_code == 403


async def test_admin_cannot_create_or_modify_owners(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    await _add_user(owner, "admin@acme.com", "admin")
    admin = await _signed_in(client_factory, "admin@acme.com")
    assert (await _add_user(admin, "o2@acme.com", "owner")).status_code == 403
    agent = (await _add_user(admin, "agent@acme.com", "agent")).json()
    promote = await admin.patch(
        f"/v1/users/{agent['id']}", headers=csrf(admin), json={"role": "owner"}
    )
    assert promote.status_code == 403
    owner_id = (await owner.get("/v1/auth/me")).json()["user"]["id"]
    demote = await admin.patch(
        f"/v1/users/{owner_id}", headers=csrf(admin), json={"is_active": False}
    )
    assert demote.status_code == 403


async def test_tenant_isolation(client_factory: Factory) -> None:
    acme = await _owner(client_factory)
    globex = await _owner(client_factory, email="owner@globex.com", company="Globex")
    acme_agent = (await _add_user(acme, "agent@acme.com", "agent")).json()

    globex_users = (await globex.get("/v1/users")).json()
    assert [u["email"] for u in globex_users] == ["owner@globex.com"]
    res = await globex.patch(
        f"/v1/users/{acme_agent['id']}", headers=csrf(globex), json={"is_active": False}
    )
    assert res.status_code == 404
    audit = (await globex.get("/v1/audit-events")).json()["items"]
    assert all(e["target_id"] != acme_agent["id"] for e in audit)


async def test_deactivation_kills_sessions_and_blocks_login(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    agent_id = (await _add_user(owner, "agent@acme.com", "agent")).json()["id"]
    agent = await _signed_in(client_factory, "agent@acme.com")

    res = await owner.patch(f"/v1/users/{agent_id}", headers=csrf(owner), json={"is_active": False})
    assert res.status_code == 200 and res.json()["is_active"] is False
    assert (await agent.get("/v1/auth/me")).status_code == 401
    assert (await login(client_factory(), "agent@acme.com")).status_code == 401

    await owner.patch(f"/v1/users/{agent_id}", headers=csrf(owner), json={"is_active": True})
    assert (await login(client_factory(), "agent@acme.com")).status_code == 200


async def test_role_change_invalidates_old_access_token(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    admin_id = (await _add_user(owner, "admin@acme.com", "admin")).json()["id"]
    admin = await _signed_in(client_factory, "admin@acme.com")
    assert (await admin.get("/v1/users")).status_code == 200

    await owner.patch(f"/v1/users/{admin_id}", headers=csrf(owner), json={"role": "agent"})
    assert (await admin.get("/v1/users")).status_code == 401
    # After a refresh the new token carries the new role.
    assert (await admin.post("/v1/auth/refresh", headers=csrf(admin))).status_code == 200
    assert (await admin.get("/v1/users")).status_code == 403


async def test_self_change_and_last_owner_guards(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    me = (await owner.get("/v1/auth/me")).json()["user"]["id"]
    for body in ({"role": "admin"}, {"is_active": False}):
        res = await owner.patch(f"/v1/users/{me}", headers=csrf(owner), json=body)
        assert res.status_code == 400

    second = (await _add_user(owner, "o2@acme.com", "owner")).json()["id"]
    o2 = await _signed_in(client_factory, "o2@acme.com")
    ok = await o2.patch(f"/v1/users/{me}", headers=csrf(o2), json={"role": "admin"})
    assert ok.status_code == 200
    last = await owner.patch(f"/v1/users/{second}", headers=csrf(owner), json={"role": "admin"})
    assert last.status_code == 401  # owner was demoted, old token is stale
    await owner.post("/v1/auth/refresh", headers=csrf(owner))
    blocked = await owner.patch(f"/v1/users/{second}", headers=csrf(owner), json={"role": "admin"})
    assert blocked.status_code == 403  # admins cannot touch the (now only) owner


async def test_duplicate_and_weak_user_creation(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    assert (await _add_user(owner, "owner@acme.com", "agent")).status_code == 409
    weak = await owner.post(
        "/v1/users",
        headers=csrf(owner),
        json={"email": "w@acme.com", "full_name": "W", "role": "agent", "password": "short"},
    )
    assert weak.status_code == 422


async def test_rename_user(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    uid = (await _add_user(owner, "agent@acme.com", "agent")).json()["id"]
    res = await owner.patch(
        f"/v1/users/{uid}", headers=csrf(owner), json={"full_name": "Ann Agent"}
    )
    assert res.json()["full_name"] == "Ann Agent"


async def test_audit_log_records_and_paginates(client_factory: Factory) -> None:
    owner = await _owner(client_factory)
    await _add_user(owner, "a1@acme.com", "agent")
    await login(client_factory(), "owner@acme.com", "wrong password here")
    await login(client_factory(), "owner@acme.com")

    page = (await owner.get("/v1/audit-events", params={"limit": 2})).json()
    assert len(page["items"]) == 2 and page["next_before"] is not None
    actions = {e["action"] for e in (await owner.get("/v1/audit-events")).json()["items"]}
    assert {"tenant.created", "user.created", "auth.login", "auth.login_failed"} <= actions
    failed = (await owner.get("/v1/audit-events", params={"action": "auth.login_failed"})).json()
    assert [e["action"] for e in failed["items"]] == ["auth.login_failed"]
    nxt = (await owner.get("/v1/audit-events", params={"before": page["next_before"]})).json()
    assert nxt["items"]


async def test_concurrent_duplicate_email_is_409_not_500(
    sessionmaker: "async_sessionmaker[AsyncSession]",
) -> None:
    """Simulates the race where the pre-check passes but the insert collides."""
    from app.models import Role, Tenant, User
    from app.services.auth_service import AuthError, add_user

    async with sessionmaker() as db:
        tenant = Tenant(name="Acme", slug="acme")
        db.add(tenant)
        await db.flush()
        await add_user(db, User(tenant_id=tenant.id, email="dup@acme.com", role=Role.AGENT))
        try:
            await add_user(db, User(tenant_id=tenant.id, email="dup@acme.com", role=Role.AGENT))
        except AuthError as err:
            assert err.status_code == 409
        else:
            raise AssertionError("expected AuthError")
        await db.commit()  # outer transaction survives the failed savepoint
