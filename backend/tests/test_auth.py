"""Registration, login, token rotation and the account guard rails."""

from __future__ import annotations

import pytest

from tests.conftest import REGISTRATION


class TestRegistration:
    async def test_creates_an_account_and_returns_tokens(self, client):
        response = await client.post("/auth/register", json=REGISTRATION)
        assert response.status_code == 201
        body = response.json()
        assert body["user"]["email"] == REGISTRATION["email"]
        assert body["user"]["role"] == "student"
        assert body["tokens"]["access_token"]
        assert body["tokens"]["expires_in"] > 0

    async def test_never_returns_the_password_hash(self, client, student):
        response = await client.get("/auth/me", headers=student["headers"])
        assert "password" not in response.text.lower()

    async def test_duplicate_email_is_rejected(self, client, student):
        response = await client.post("/auth/register", json=REGISTRATION)
        assert response.status_code == 409

    @pytest.mark.parametrize("password", ["short1!", "allletters", "12345678"])
    async def test_weak_passwords_are_rejected(self, client, password):
        response = await client.post(
            "/auth/register", json={**REGISTRATION, "email": "x@y.pk", "password": password}
        )
        assert response.status_code == 422


class TestLogin:
    async def test_valid_credentials(self, client, student):
        response = await client.post(
            "/auth/login",
            json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
        )
        assert response.status_code == 200

    async def test_wrong_password_and_unknown_email_look_identical(self, client, student):
        wrong = await client.post(
            "/auth/login", json={"email": REGISTRATION["email"], "password": "Wrong!2026"}
        )
        unknown = await client.post(
            "/auth/login", json={"email": "nobody@example.pk", "password": "Wrong!2026"}
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["detail"] == unknown.json()["detail"]


class TestTokens:
    async def test_refresh_rotates_the_token(self, client, student):
        response = await client.post(
            "/auth/refresh", json={"refresh_token": student["tokens"]["refresh_token"]}
        )
        assert response.status_code == 200
        assert response.json()["refresh_token"] != student["tokens"]["refresh_token"]

    async def test_replaying_a_rotated_token_kills_the_session_family(self, client, student):
        original = student["tokens"]["refresh_token"]
        rotated = (await client.post("/auth/refresh", json={"refresh_token": original})).json()

        replay = await client.post("/auth/refresh", json={"refresh_token": original})
        assert replay.status_code == 401

        # The replay is treated as a compromise, so the new token dies too.
        after = await client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
        assert after.status_code == 401

    async def test_an_access_token_cannot_be_used_to_refresh(self, client, student):
        response = await client.post(
            "/auth/refresh", json={"refresh_token": student["tokens"]["access_token"]}
        )
        assert response.status_code == 401

    async def test_protected_routes_need_a_token(self, client):
        assert (await client.get("/auth/me")).status_code == 401
        assert (await client.get("/me/dashboard")).status_code == 401

    async def test_garbage_token_is_rejected(self, client):
        response = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401


class TestAuthorisation:
    async def test_students_cannot_reach_admin_endpoints(self, client, student, seeded):
        response = await client.get("/admin/questions", headers=student["headers"])
        assert response.status_code == 403

    async def test_admin_can(self, client, admin):
        response = await client.get("/admin/questions", headers=admin["headers"])
        assert response.status_code == 200

    async def test_super_admin_cannot_edit_their_own_account(self, client, admin):
        response = await client.patch(
            f"/admin/users/{admin['user']['id']}",
            json={"role": "student"},
            headers=admin["headers"],
        )
        assert response.status_code == 400


class TestPasswordChange:
    async def test_requires_the_current_password(self, client, student):
        response = await client.post(
            "/auth/change-password",
            json={"current_password": "Wrong!2026", "new_password": "Newpass!2026"},
            headers=student["headers"],
        )
        assert response.status_code == 400

    async def test_succeeds_and_revokes_sessions(self, client, student):
        response = await client.post(
            "/auth/change-password",
            json={
                "current_password": REGISTRATION["password"],
                "new_password": "Newpass!2026",
            },
            headers=student["headers"],
        )
        assert response.status_code == 200

        stale = await client.post(
            "/auth/refresh", json={"refresh_token": student["tokens"]["refresh_token"]}
        )
        assert stale.status_code == 401
