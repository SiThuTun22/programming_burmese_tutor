"""AAA Litestar app CORS."""

from litestar.testing import TestClient

from app.main import create_app


def test_health_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_cors_allows_vite_origin() -> None:
    with TestClient(create_app()) as client:
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == (
            "http://localhost:5173"
        )
