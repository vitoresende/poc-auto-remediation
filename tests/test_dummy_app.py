"""Tests for the Sentry Dummy App & offline fixture generation (Package 1.2 & 1.3)."""

from fastapi.testclient import TestClient

from dummy_app.main import app
from dummy_app.services.auth_billing_service import (
    process_recurring_charge,
    reconcile_settlement_batch,
)
from dummy_app.services.checkout_service import (
    apply_promotional_discount,
    calculate_installment_plan,
)

client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "dummy-app"
    assert body["sentry"]["send_default_pii"] is True
    assert body["sentry"]["include_local_variables"] is True


def test_happy_path_services_when_inputs_are_valid() -> None:
    discount_result = apply_promotional_discount(
        {
            "subtotal": 200.0,
            "discount": {"percentage": 10.0},
            "customer": {"email": "ok@example.com", "cpf": "111.222.333-44"},
        }
    )
    assert discount_result["final_total"] == 180.0

    installment_result = calculate_installment_plan(
        {
            "amount": 300.0,
            "cashback_credit": 0.0,
            "installments": 3,
            "payer": {"email": "ok@example.com"},
        }
    )
    assert installment_result["installment_value"] == 100.0

    billing_result = process_recurring_charge(
        {
            "base_plan_price": 100.0,
            "gateway_fee_override": 5.5,
            "account": {"email": "ok@example.com"},
        }
    )
    assert billing_result["total_charge"] == 105.5

    settlement_result = reconcile_settlement_batch(
        {
            "batch_id": "BATCH-OK",
            "customer_context": {"email": "ok@example.com"},
            "transactions": [{"tx_id": "TX-1", "settlement_code": "stl-900", "amount": 50.0}],
        }
    )
    assert settlement_result["settlement_code"] == "STL-900"


def test_scenario_endpoints_capture_sentry_events_with_pii_and_save_fixtures() -> None:
    scenarios = [
        ("discount-bug", "discount_none_bug", "TypeError"),
        ("zero-division", "zero_division_installments", "ZeroDivisionError"),
        ("type-mismatch", "type_mismatch_billing", "TypeError"),
        ("breadcrumb-flood", "breadcrumb_flood_settlement", "AttributeError"),
    ]

    for route_slug, scenario_slug, expected_exc in scenarios:
        response = client.post(
            f"/api/scenarios/{route_slug}?user_email=test.user@enterprise.io",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
                "X-Customer-CPF": "123.456.789-00",
            },
        )
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error_captured"
        assert data["scenario_slug"] == scenario_slug
        assert data["exception_type"] == expected_exc
        assert data["sentry_event_id"] is not None
        assert data["saved_fixture"] == f"fixtures/sentry_{scenario_slug}.json"

        event_preview = data["sentry_payload_preview"]
        assert event_preview is not None
        assert "exception" in event_preview
        assert "breadcrumbs" in event_preview
        assert "user" in event_preview

    fixtures_res = client.get("/api/fixtures")
    assert fixtures_res.status_code == 200
    fixture_names = [item["name"] for item in fixtures_res.json()["fixtures"]]
    for _, scenario_slug, _ in scenarios:
        assert f"sentry_{scenario_slug}.json" in fixture_names
