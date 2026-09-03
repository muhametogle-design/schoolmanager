"""E2E tests: finance & fees module (fee structures, invoices, payments, balances)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import API


def _post_invoice(
    client: TestClient,
    *,
    student_id: int,
    fee_structure_id: int | None = None,
    amount_cents: int | None = None,
    description: str | None = None,
    issue_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    payload = {
        "student_id": student_id,
        "fee_structure_id": fee_structure_id,
        "amount_cents": amount_cents,
        "description": description,
        "issue_date": issue_date,
        "due_date": due_date,
    }
    response = client.post(f"{API}/finance/invoices", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# -- fee structures ----------------------------------------------------------


def test_fee_structure_create_read_and_list(
    client: TestClient, school_id: int, fee_structure_id: int
) -> None:
    single = client.get(f"{API}/finance/fee-structures/{fee_structure_id}")
    assert single.status_code == 200
    body = single.json()
    assert body["amount_cents"] == 450_000
    assert body["currency"] == "USD"
    assert body["is_active"] is True

    listed = client.get(f"{API}/finance/fee-structures", params={"school_id": school_id})
    assert listed.status_code == 200
    assert [entry["id"] for entry in listed.json()] == [fee_structure_id]


def test_fee_structure_duplicate_name_per_school_is_400(
    client: TestClient, school_id: int, fee_structure_id: int
) -> None:
    existing = client.get(f"{API}/finance/fee-structures/{fee_structure_id}")
    assert existing.status_code == 200

    response = client.post(
        f"{API}/finance/fee-structures",
        json={"school_id": school_id, "name": existing.json()["name"], "amount_cents": 100},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_fee_structure_unknown_school_is_404(client: TestClient) -> None:
    response = client.post(
        f"{API}/finance/fee-structures",
        json={"school_id": 4242, "name": "Ghost fee", "amount_cents": 100},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "school 4242 not found"


def test_missing_fee_structure_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/finance/fee-structures/31337")
    assert response.status_code == 404
    assert response.json()["detail"] == "fee structure 31337 not found"


def test_negative_fee_amount_is_422(client: TestClient, school_id: int) -> None:
    response = client.post(
        f"{API}/finance/fee-structures",
        json={"school_id": school_id, "name": "Bad fee", "amount_cents": -5},
    )
    assert response.status_code == 422


# -- invoices --------------------------------------------------------------------


def test_invoice_inherits_fee_amount_and_numbering(
    client: TestClient, invoice_id: int, student_id: int, fee_structure_id: int
) -> None:
    assert invoice_id == 1  # first invoice in a fresh database
    fetched = client.get(f"{API}/finance/invoices/{invoice_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == invoice_id
    assert body["student_id"] == student_id
    assert body["student_name"] == "Ada Lovelace"
    assert body["fee_structure_id"] == fee_structure_id
    assert body["fee_structure_name"] == "Tuition Term 1"
    assert body["amount_cents"] == 450_000
    assert body["paid_cents"] == 0
    assert body["balance_cents"] == 450_000
    assert body["status"] == "issued"
    assert body["is_overdue"] is False
    assert body["number"] == f"INV-{date.today().year}-00001"


def test_invoice_with_explicit_amount_override(client: TestClient, student_id: int) -> None:
    body = _post_invoice(
        client, student_id=student_id, amount_cents=12_345, description="Lost library book"
    )
    assert body["amount_cents"] == 12_345
    assert body["currency"] == "USD"
    assert body["fee_structure_id"] is None


def test_invoice_without_amount_or_fee_is_400(client: TestClient, student_id: int) -> None:
    response = client.post(f"{API}/finance/invoices", json={"student_id": student_id})
    assert response.status_code == 400
    assert "amount_cents is required" in response.json()["detail"]


def test_invoice_custom_amount_requires_description(
    client: TestClient, student_id: int
) -> None:
    response = client.post(
        f"{API}/finance/invoices",
        json={"student_id": student_id, "amount_cents": 500},
    )
    assert response.status_code == 400
    assert "description is required" in response.json()["detail"]


def test_invoice_unknown_student_is_404(client: TestClient, fee_structure_id: int) -> None:
    response = client.post(
        f"{API}/finance/invoices",
        json={"student_id": 77777, "fee_structure_id": fee_structure_id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "student 77777 not found"


def test_invoice_across_schools_is_400(
    client: TestClient, student_id: int, fee_structure_id: int
) -> None:
    home_student = client.get(f"{API}/management/students/{student_id}").json()
    other_school = client.post(
        f"{API}/management/schools", json={"name": "Other School", "code": "OTH-01"}
    ).json()
    assert other_school["id"] != home_student["school_id"]
    other_student = client.post(
        f"{API}/management/students",
        json={
            "school_id": other_school["id"],
            "first_name": "Grace",
            "last_name": "Hopper",
        },
    ).json()
    response = client.post(
        f"{API}/finance/invoices",
        json={"student_id": other_student["id"], "fee_structure_id": fee_structure_id},
    )
    assert response.status_code == 400
    assert "different school" in response.json()["detail"]


def test_invoice_due_before_issue_is_400(client: TestClient, student_id: int) -> None:
    today = date.today()
    response = client.post(
        f"{API}/finance/invoices",
        json={
            "student_id": student_id,
            "amount_cents": 1000,
            "description": "Odd bill",
            "issue_date": today.isoformat(),
            "due_date": (today - timedelta(days=3)).isoformat(),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "due_date cannot be earlier than issue_date"


def test_invoice_inactive_fee_structure_is_400(
    client: TestClient, school_id: int, student_id: int
) -> None:
    fee = client.post(
        f"{API}/finance/fee-structures",
        json={
            "school_id": school_id,
            "name": "Retired fee",
            "amount_cents": 900,
            "is_active": False,
        },
    ).json()
    response = client.post(
        f"{API}/finance/invoices",
        json={"student_id": student_id, "fee_structure_id": fee["id"]},
    )
    assert response.status_code == 400
    assert "inactive" in response.json()["detail"]


def test_missing_invoice_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/finance/invoices/4242").status_code == 404
    missing = client.get(f"{API}/finance/invoices/4242/balance")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "invoice 4242 not found"


def test_overdue_flag_when_due_date_passed(client: TestClient, student_id: int) -> None:
    past = date.today() - timedelta(days=10)
    body = _post_invoice(
        client,
        student_id=student_id,
        amount_cents=7000,
        description="Old term balance",
        issue_date=(past - timedelta(days=40)).isoformat(),
        due_date=past.isoformat(),
    )
    assert body["is_overdue"] is True
    balance = client.get(f"{API}/finance/invoices/{body['id']}/balance").json()
    assert balance["is_overdue"] is True
    assert balance["balance_cents"] == 7000


# -- payments -----------------------------------------------------------------------


def test_partial_payment_updates_status_and_balance(
    client: TestClient, invoice_id: int
) -> None:
    response = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments",
        json={"amount_cents": 150_000, "method": "bank_transfer", "reference": "TRX-001"},
    )
    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment["receipt_number"] == f"RCP-{date.today().year}-00001"
    assert payment["method"] == "bank_transfer"

    balance = client.get(f"{API}/finance/invoices/{invoice_id}/balance").json()
    assert balance["paid_cents"] == 150_000
    assert balance["balance_cents"] == 300_000
    assert balance["status"] == "partially_paid"

    listed = client.get(f"{API}/finance/invoices/{invoice_id}/payments")
    assert listed.status_code == 200
    assert [entry["id"] for entry in listed.json()] == [payment["id"]]


def test_full_payment_chain_sets_paid(client: TestClient, invoice_id: int) -> None:
    for amount in (200_000, 250_000):
        response = client.post(
            f"{API}/finance/invoices/{invoice_id}/payments", json={"amount_cents": amount}
        )
        assert response.status_code == 201

    invoice = client.get(f"{API}/finance/invoices/{invoice_id}").json()
    assert invoice["status"] == "paid"
    assert invoice["paid_cents"] == 450_000
    assert invoice["balance_cents"] == 0
    assert [p["amount_cents"] for p in invoice["payments"]] == [200_000, 250_000]

    # paying a settled invoice is a 400 business error
    extra = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments", json={"amount_cents": 1}
    )
    assert extra.status_code == 400
    assert "already fully paid" in extra.json()["detail"]


def test_overpayment_is_rejected_with_400(client: TestClient, invoice_id: int) -> None:
    response = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments",
        json={"amount_cents": 450_001},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "exceeds the outstanding balance" in detail
    assert "450000 cents" in detail


def test_zero_and_negative_payment_amounts_are_422(
    client: TestClient, invoice_id: int
) -> None:
    for amount in (0, -250):
        response = client.post(
            f"{API}/finance/invoices/{invoice_id}/payments", json={"amount_cents": amount}
        )
        assert response.status_code == 422


def test_invalid_payment_method_is_422(client: TestClient, invoice_id: int) -> None:
    response = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments",
        json={"amount_cents": 100, "method": "carrier_pigeon"},
    )
    assert response.status_code == 422


def test_payment_on_unknown_invoice_is_404(client: TestClient) -> None:
    response = client.post(
        f"{API}/finance/invoices/99999/payments", json={"amount_cents": 100}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "invoice 99999 not found"


def test_unique_receipt_numbers(client: TestClient, invoice_id: int, student_id: int) -> None:
    second_invoice = _post_invoice(
        client, student_id=student_id, amount_cents=5000, description="Clubs fee"
    )
    first = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments", json={"amount_cents": 100}
    ).json()
    second = client.post(
        f"{API}/finance/invoices/{second_invoice['id']}/payments", json={"amount_cents": 5000}
    ).json()
    assert first["receipt_number"] != second["receipt_number"]


# -- voiding -----------------------------------------------------------------------------


def test_void_flow_and_guardrails(client: TestClient, invoice_id: int, student_id: int) -> None:
    # invoice with payments cannot be voided
    paid = _post_invoice(client, student_id=student_id, amount_cents=8000, description="Field trip")
    client.post(f"{API}/finance/invoices/{paid['id']}/payments", json={"amount_cents": 1000})
    refused = client.post(f"{API}/finance/invoices/{paid['id']}/void")
    assert refused.status_code == 400
    assert "recorded payments" in refused.json()["detail"]

    # clean invoice can be voided, then blocks payments and double-voids
    voided = client.post(f"{API}/finance/invoices/{invoice_id}/void")
    assert voided.status_code == 200
    assert voided.json()["status"] == "void"

    blocked = client.post(
        f"{API}/finance/invoices/{invoice_id}/payments", json={"amount_cents": 100}
    )
    assert blocked.status_code == 400
    assert "void invoice" in blocked.json()["detail"]

    double = client.post(f"{API}/finance/invoices/{invoice_id}/void")
    assert double.status_code == 400
    assert "already void" in double.json()["detail"]


def test_void_of_unknown_invoice_is_404(client: TestClient) -> None:
    assert client.post(f"{API}/finance/invoices/31337/void").status_code == 404


# -- listing & aggregate balances -----------------------------------------------------


def test_invoice_listing_filters(
    client: TestClient, invoice_id: int, student_id: int
) -> None:
    extra = _post_invoice(
        client, student_id=student_id, amount_cents=1500, description="Late fee"
    )
    issued = client.get(f"{API}/finance/invoices", params={"status": "issued"}).json()
    assert {entry["id"] for entry in issued} == {invoice_id, extra["id"]}

    by_student = client.get(
        f"{API}/finance/invoices", params={"student_id": student_id}
    ).json()
    assert len(by_student) == 2

    unknown = client.get(
        f"{API}/finance/invoices", params={"student_id": 55555}
    )
    assert unknown.status_code == 404

    bad_status = client.get(f"{API}/finance/invoices", params={"status": "exploded"})
    assert bad_status.status_code == 422


def test_student_balance_aggregates_excluding_void(
    client: TestClient, student_id: int, invoice_id: int
) -> None:
    # the invoice_id fixture bills 450000 with no payments yet
    first_balance = client.get(f"{API}/finance/invoices/{invoice_id}/balance").json()
    assert first_balance["balance_cents"] == 450_000
    paid = _post_invoice(client, student_id=student_id, amount_cents=10_000, description="Lab fee")
    client.post(f"{API}/finance/invoices/{paid['id']}/payments", json={"amount_cents": 4000})
    voidable = _post_invoice(
        client, student_id=student_id, amount_cents=999_999, description="To be voided"
    )
    client.post(f"{API}/finance/invoices/{voidable['id']}/void")

    balance = client.get(f"{API}/finance/students/{student_id}/balance")
    assert balance.status_code == 200
    body = balance.json()
    assert body["full_name"] == "Ada Lovelace"
    assert body["currency"] == "USD"
    assert body["invoice_count"] == 2
    assert body["invoiced_cents"] == 460_000
    assert body["paid_cents"] == 4_000
    assert body["balance_cents"] == 456_000
    assert body["open_invoice_count"] == 2
    assert body["overdue_invoice_count"] == 0


def test_student_balance_with_no_invoices(client: TestClient, school_id: int) -> None:
    lonely = client.post(
        f"{API}/management/students",
        json={"school_id": school_id, "first_name": "Fresh", "last_name": "Face"},
    ).json()
    body = client.get(f"{API}/finance/students/{lonely['id']}/balance").json()
    assert body["balance_cents"] == 0
    assert body["invoice_count"] == 0


def test_student_balance_unknown_student_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/finance/students/202020/balance")
    assert response.status_code == 404
    assert response.json()["detail"] == "student 202020 not found"


def test_payment_listing_filters(client: TestClient, student_id: int, invoice_id: int) -> None:
    client.post(
        f"{API}/finance/invoices/{invoice_id}/payments",
        json={"amount_cents": 5000, "method": "cash"},
    )
    mine = client.get(f"{API}/finance/payments", params={"student_id": student_id}).json()
    assert len(mine) == 1
    by_card = client.get(f"{API}/finance/payments", params={"method": "card"}).json()
    assert by_card == []
    unknown = client.get(f"{API}/finance/payments", params={"invoice_id": 987})
    assert unknown.status_code == 404
