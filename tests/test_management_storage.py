"""E2E tests: management CRUD + real file-system uploads (avatars/logos)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from tests.conftest import API, TINY_PNG


def _png_upload() -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("avatar.png", TINY_PNG, "image/png")}


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_school_normalises_code_and_lists(client: TestClient, school_id: int) -> None:
    school = client.get(f"{API}/management/schools/{school_id}").json()
    assert school["code"] == "NE-ES-01"
    assert school["logo_url"] is None

    listing = client.get(f"{API}/management/schools")
    assert listing.status_code == 200
    assert [entry["id"] for entry in listing.json()] == [school_id]


def test_duplicate_school_code_rejected_with_400(client: TestClient, school_id: int) -> None:
    existing = client.get(f"{API}/management/schools/{school_id}").json()
    response = client.post(
        f"{API}/management/schools",
        json={"name": "Copycat School", "code": existing["code"]},
    )
    assert response.status_code == 400
    assert "already in use" in response.json()["detail"]


def test_school_not_found_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/management/schools/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "school 9999 not found"


def test_create_student_requires_existing_school(client: TestClient) -> None:
    response = client.post(
        f"{API}/management/students",
        json={"school_id": 12345, "first_name": "Orphan", "last_name": "Anonymous"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "school 12345 not found"


def test_invalid_email_shape_is_422(client: TestClient, school_id: int) -> None:
    response = client.post(
        f"{API}/management/students",
        json={"school_id": school_id, "first_name": "A", "last_name": "B", "email": "nope"},
    )
    assert response.status_code == 422


def test_duplicate_student_email_rejected_with_400(
    client: TestClient, school_id: int, student_id: int
) -> None:
    seeded = client.get(f"{API}/management/students/{student_id}").json()
    assert seeded["email"] == "ada@example.com"
    response = client.post(
        f"{API}/management/students",
        json={
            "school_id": school_id,
            "first_name": "Another",
            "last_name": "Student",
            "email": "ada@example.com",
        },
    )
    assert response.status_code == 400
    assert "already assigned" in response.json()["detail"]


def test_update_student_patch_and_noop(client: TestClient, student_id: int) -> None:
    response = client.patch(
        f"{API}/management/students/{student_id}", json={"grade_label": "7A"}
    )
    assert response.status_code == 200
    assert response.json()["grade_label"] == "7A"

    empty = client.patch(f"{API}/management/students/{student_id}", json={})
    assert empty.status_code == 400
    assert empty.json()["detail"] == "no fields to update"


def test_upload_avatar_writes_file_and_serves_it(
    client: TestClient, student_id: int, uploads_root: Path
) -> None:
    response = client.post(
        f"{API}/management/students/{student_id}/avatar", files=_png_upload()
    )
    assert response.status_code == 200, response.text
    body = response.json()
    filename = body["avatar_filename"]
    assert filename is not None
    assert filename.startswith(f"student-{student_id}_")
    assert body["avatar_url"] == f"/static/uploads/avatars/{filename}"

    # file-system side effects
    stored = uploads_root / "avatars" / filename
    assert stored.is_file()
    assert stored.read_bytes() == TINY_PNG
    assert not list(uploads_root.rglob(".tmp_*")), "temp files must not leak"

    # public serving through the /static mount
    served = client.get(body["avatar_url"])
    assert served.status_code == 200
    assert served.content == TINY_PNG
    assert served.headers["content-type"].startswith("image/png")

    # persisted on the student record
    student = client.get(f"{API}/management/students/{student_id}").json()
    assert student["avatar_filename"] == filename


def test_avatar_replacement_removes_previous_file(
    client: TestClient, student_id: int, uploads_root: Path
) -> None:
    first = client.post(
        f"{API}/management/students/{student_id}/avatar", files=_png_upload()
    ).json()
    second = client.post(
        f"{API}/management/students/{student_id}/avatar", files=_png_upload()
    ).json()

    assert first["avatar_filename"] != second["avatar_filename"]
    assert not (uploads_root / "avatars" / first["avatar_filename"]).exists()
    assert (uploads_root / "avatars" / second["avatar_filename"]).is_file()
    assert len(list((uploads_root / "avatars").iterdir())) == 1


def test_avatar_upload_rejects_non_image_bytes(client: TestClient, student_id: int) -> None:
    response = client.post(
        f"{API}/management/students/{student_id}/avatar",
        files={"file": ("evil.png", b"this is not an image", "image/png")},
    )
    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"]


def test_avatar_upload_rejects_content_type_mismatch(
    client: TestClient, student_id: int
) -> None:
    response = client.post(
        f"{API}/management/students/{student_id}/avatar",
        files={"file": ("photo.jpg", TINY_PNG, "image/jpeg")},  # bytes are PNG
    )
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_avatar_upload_rejects_empty_file(client: TestClient, student_id: int) -> None:
    response = client.post(
        f"{API}/management/students/{student_id}/avatar",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "uploaded file is empty"


def test_avatar_upload_rejects_oversize_file(
    client: TestClient, settings: Settings, student_id: int
) -> None:
    oversized = TINY_PNG + b"\x00" * (settings.max_upload_bytes + 1)
    response = client.post(
        f"{API}/management/students/{student_id}/avatar",
        files={"file": ("huge.png", oversized, "image/png")},
    )
    assert response.status_code == 413
    assert "exceeding" in response.json()["detail"]


def test_avatar_upload_missing_file_field_is_422(client: TestClient, student_id: int) -> None:
    response = client.post(f"{API}/management/students/{student_id}/avatar", files={})
    assert response.status_code == 422


def test_avatar_upload_for_unknown_student_is_404(client: TestClient) -> None:
    response = client.post(f"{API}/management/students/987654/avatar", files=_png_upload())
    assert response.status_code == 404
    assert response.json()["detail"] == "student 987654 not found"


def test_remove_avatar_deletes_file(
    client: TestClient, student_id: int, uploads_root: Path
) -> None:
    upload = client.post(
        f"{API}/management/students/{student_id}/avatar", files=_png_upload()
    ).json()
    stored = uploads_root / "avatars" / upload["avatar_filename"]
    assert stored.is_file()

    response = client.delete(f"{API}/management/students/{student_id}/avatar")
    assert response.status_code == 200
    assert response.json()["avatar_url"] is None
    assert not stored.exists()

    # removing again is a no-op, still 200
    again = client.delete(f"{API}/management/students/{student_id}/avatar")
    assert again.status_code == 200


def test_school_logo_upload_and_serving(
    client: TestClient, school_id: int, uploads_root: Path
) -> None:
    response = client.post(
        f"{API}/management/schools/{school_id}/logo",
        files={"file": ("logo.png", TINY_PNG, "image/png")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    logo_url = body["logo_url"]
    assert logo_url == f"/static/uploads/logos/{body['logo_filename']}"
    assert (uploads_root / "logos" / body["logo_filename"]).read_bytes() == TINY_PNG

    served = client.get(logo_url)
    assert served.status_code == 200
    assert served.content == TINY_PNG

    removed = client.delete(f"{API}/management/schools/{school_id}/logo")
    assert removed.status_code == 200
    assert removed.json()["logo_url"] is None
    assert list((uploads_root / "logos").iterdir()) == []


def test_logo_upload_for_unknown_school_is_404(client: TestClient) -> None:
    response = client.post(
        f"{API}/management/schools/9999/logo", files=_png_upload()
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "school 9999 not found"


def test_static_mount_returns_404_for_missing_file(client: TestClient) -> None:
    response = client.get("/static/uploads/avatars/does-not-exist.png")
    assert response.status_code == 404


def test_unknown_api_route_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/management/unicorns").status_code == 404
