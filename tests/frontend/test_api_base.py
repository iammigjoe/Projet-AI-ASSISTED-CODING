"""
===============================================================================
Tests : api_base
===============================================================================
Objectif :
    Vérifier que le client HTTP du frontend envoie le jeton, et transforme
    toute erreur (API ou réseau) en ApiError lisible.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import httpx
import pytest

from frontend.api.base import ApiClient, ApiError


def _client(handler, token="access-123") -> ApiClient:
    return ApiClient(
        "http://api.test", token_getter=lambda: token, transport=httpx.MockTransport(handler)
    )


def test_request_sends_bearer_token_and_prefix():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[{"id": 1}])

    assert _client(handler).get("/courses") == [{"id": 1}]
    assert seen == {"url": "http://api.test/courses", "auth": "Bearer access-123"}


def test_request_without_token_sends_no_authorization():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={})

    _client(handler, token=None).get("/health")

    assert seen["auth"] is None


def test_api_error_body_becomes_api_error():
    def handler(request):
        body = {"error": {"code": "PLAN_NOT_FEASIBLE", "message": "Il manque 6 h.", "details": {}}}
        return httpx.Response(422, json=body)

    with pytest.raises(ApiError) as caught:
        _client(handler).post("/plans", json={})

    assert (caught.value.status_code, caught.value.code) == (422, "PLAN_NOT_FEASIBLE")
    assert caught.value.message == "Il manque 6 h."


def test_unexpected_error_body_becomes_generic_api_error():
    def handler(request):
        return httpx.Response(502, text="<html>Bad gateway</html>")

    with pytest.raises(ApiError) as caught:
        _client(handler).get("/courses")

    assert caught.value.code == "UNEXPECTED_RESPONSE"


def test_network_failure_becomes_api_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(ApiError) as caught:
        _client(handler).get("/courses")

    assert caught.value.code == "NETWORK_ERROR"


def test_no_content_returns_none():
    def handler(request):
        return httpx.Response(204)

    assert _client(handler).delete("/courses/1") is None


def test_unauthorized_response_is_refreshed_then_replayed_once():
    tokens = iter(["expired", "fresh"])
    current = {"token": next(tokens)}
    calls = []

    def handler(request):
        calls.append(request.headers.get("Authorization"))
        if request.headers.get("Authorization") == "Bearer fresh":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(401, json={"error": {"code": "UNAUTHORIZED", "message": "x"}})

    def refresher():
        current["token"] = next(tokens)
        return True

    client = ApiClient(
        "http://api.test",
        token_getter=lambda: current["token"],
        refresher=refresher,
        transport=httpx.MockTransport(handler),
    )

    assert client.get("/courses") == {"ok": True}
    assert calls == ["Bearer expired", "Bearer fresh"]


def test_failed_refresh_raises_unauthorized():
    def handler(request):
        return httpx.Response(401, json={"error": {"code": "UNAUTHORIZED", "message": "x"}})

    client = ApiClient(
        "http://api.test",
        token_getter=lambda: "expired",
        refresher=lambda: False,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ApiError) as caught:
        client.get("/courses")

    assert caught.value.code == "UNAUTHORIZED"


def test_public_route_sends_no_token_and_never_refreshes():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(401, json={"error": {"code": "INVALID_CREDENTIALS", "message": "x"}})

    def refresher():
        raise AssertionError("une route publique ne doit pas renouveler les jetons")

    client = ApiClient(
        "http://api.test",
        token_getter=lambda: "token",
        refresher=refresher,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ApiError):
        client.post("/auth/login", json={}, authenticated=False)
    assert seen["auth"] is None
