"""Shared e2e fixtures: isolated app instance + seeded records.

Every test gets a fresh SQLite file and uploads directory under ``tmp_path``,
built through the production ``create_app`` wiring (real routers, real storage
service, real StaticFiles mount).
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

#: 1x1 transparent PNG — valid magic bytes, tiny payload.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

API = "/api/v1"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'schoolmanager-test.db'}",
        static_root=tmp_path / "static",
    )


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def uploads_root(settings: Settings) -> Path:
    return settings.uploads_root


@pytest.fixture()
def school_id(client: TestClient) -> int:
    response = client.post(
        f"{API}/management/schools",
        json={
            "name": "Near East Elementary School",
            "code": "ne-es-01",
            "email": "office@ne-es.example",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture()
def student_id(client: TestClient, school_id: int) -> int:
    response = client.post(
        f"{API}/management/students",
        json={
            "school_id": school_id,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "grade_label": "6B",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture()
def fee_structure_id(client: TestClient, school_id: int) -> int:
    response = client.post(
        f"{API}/finance/fee-structures",
        json={
            "school_id": school_id,
            "name": "Tuition Term 1",
            "category": "tuition",
            "amount_cents": 450_000,
            "description": "Fall term tuition",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture()
def invoice_id(client: TestClient, student_id: int, fee_structure_id: int) -> int:
    response = client.post(
        f"{API}/finance/invoices",
        json={"student_id": student_id, "fee_structure_id": fee_structure_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
