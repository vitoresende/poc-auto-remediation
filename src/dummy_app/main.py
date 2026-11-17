import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sentry_sdk

from dummy_app.config import settings
from dummy_app.sentry_setup import (
    get_last_event_for_scenario,
    get_sentry_status,
    init_sentry,
)
from dummy_app.services.auth_billing_service import (
    process_recurring_charge,
    reconcile_settlement_batch,
)
from dummy_app.services.checkout_service import (
    apply_promotional_discount,
    calculate_installment_plan,
)
from dummy_app.ui import DASHBOARD_HTML

init_sentry()

app = FastAPI(
    title="Sentry Dummy App — Auto-Remediation Agent PoC",
    description=(
        "Target test application (Package 1.2 & 1.3) for controlled generation of runtime exceptions "
        "containing PII (CPF, SSN, Credit Cards, Passwords, Bearer Tokens, and Emails) in Sentry."
    ),
    version="0.1.0",
)


class SentryDsnUpdate(BaseModel):
    sentry_dsn: str = ""


def _configure_sentry_scope_with_pii(
    scope: Any,
    request: Request,
    scenario_slug: str,
    user_info: dict[str, Any],
    request_payload: dict[str, Any],
) -> None:
    """Attach rich PII context (user, tags, headers, body) to the active Sentry scope."""
    scope.set_tag("scenario_slug", scenario_slug)
    scope.set_tag("poc_package", "package_1_dummy_app")
    scope.set_tag("customer_cpf", user_info.get("cpf", ""))
    scope.set_user(user_info)
    scope.set_context(
        "http_request_pii",
        {
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "raw_body": request_payload,
        },
    )


def _capture_and_build_response(
    exc: Exception,
    scenario_slug: str,
    raise_unhandled: bool,
) -> JSONResponse:
    """Capture exception in Sentry, flush events to fixture/transport, and return diagnostic JSON."""
    event_id = sentry_sdk.capture_exception(exc)
    sentry_sdk.flush(timeout=2.0)

    if raise_unhandled:
        raise exc

    captured_entry = get_last_event_for_scenario(scenario_slug) or {}
    saved_paths = captured_entry.get("saved_paths") or {}

    return JSONResponse(
        status_code=500,
        content={
            "status": "error_captured",
            "scenario_slug": scenario_slug,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "sentry_event_id": event_id,
            "sent_to_remote_sentry": bool(settings.sentry_dsn),
            "saved_fixture": saved_paths.get("canonical_fixture"),
            "timestamped_fixture": saved_paths.get("timestamped_fixture"),
            "sentry_payload_preview": captured_entry.get("event"),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Render the interactive error & PII trigger dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
async def healthcheck() -> dict[str, Any]:
    """Healthcheck endpoint for readiness probes and CI validation."""
    return {
        "status": "ok",
        "service": "dummy-app",
        "sentry": get_sentry_status(),
    }


@app.get("/api/config/sentry")
async def read_sentry_config() -> dict[str, Any]:
    """Return active Sentry SDK and local fixture settings."""
    return get_sentry_status()


@app.post("/api/config/sentry")
async def update_sentry_config(payload: SentryDsnUpdate) -> dict[str, Any]:
    """Dynamically update SENTRY_DSN and re-initialize the Sentry SDK."""
    return init_sentry(custom_dsn=payload.sentry_dsn)


@app.get("/api/fixtures")
async def list_saved_fixtures() -> dict[str, Any]:
    """List canonical Sentry JSON fixtures generated in fixtures/."""
    fixtures_dir = settings.fixtures_dir
    if not fixtures_dir.exists():
        return {"fixtures": []}

    files = sorted(fixtures_dir.glob("sentry_*.json"))
    return {
        "fixtures": [
            {
                "name": f.name,
                "relative_path": f"fixtures/{f.name}",
                "size_bytes": f.stat().st_size,
            }
            for f in files
        ]
    }


@app.get("/api/fixtures/{filename}")
async def get_fixture_content(filename: str) -> dict[str, Any]:
    """Return the raw JSON content of a generated Sentry fixture file."""
    if "/" in filename or "\\" in filename or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid fixture filename")

    target_path = settings.fixtures_dir / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Fixture not found")

    return json.loads(target_path.read_text(encoding="utf-8"))


@app.post("/api/scenarios/discount-bug")
async def trigger_discount_bug(
    request: Request,
    raise_unhandled: bool = Query(default=False),
) -> JSONResponse:
    """Scenario 1: Trigger TypeError on NoneType discount with CPF, card, CVV, and email."""
    scenario_slug = "discount_none_bug"
    order_payload = {
        "order_id": "ORD-2026-9981",
        "subtotal": 459.90,
        "discount": None,
        "customer": {
            "full_name": "Jane Marie Doe",
            "email": "jane.doe@enterprise.io",
            "cpf": "123.456.789-00",
            "phone": "+1-415-555-0198",
        },
        "payment_card": {
            "holder": "JANE M DOE",
            "number": "4532-7788-9900-1234",
            "cvv": "842",
            "expiration": "09/29",
        },
    }

    with sentry_sdk.new_scope() as scope:
        _configure_sentry_scope_with_pii(
            scope=scope,
            request=request,
            scenario_slug=scenario_slug,
            user_info={
                "id": "usr_88412",
                "username": "jane.doe",
                "email": "jane.doe@enterprise.io",
                "ip_address": "187.45.122.91",
                "cpf": "123.456.789-00",
            },
            request_payload=order_payload,
        )
        try:
            apply_promotional_discount(order_payload)
        except Exception as exc:
            return _capture_and_build_response(exc, scenario_slug, raise_unhandled)

    return JSONResponse(status_code=200, content={"status": "unexpected_success"})


@app.post("/api/scenarios/zero-division")
async def trigger_zero_division(
    request: Request,
    raise_unhandled: bool = Query(default=False),
) -> JSONResponse:
    """Scenario 2: Trigger ZeroDivisionError on installment calculation with SSN, CPF, and card."""
    scenario_slug = "zero_division_installments"
    payment_payload = {
        "payment_id": "PAY-2026-4410",
        "amount": 1299.00,
        "cashback_credit": 99.00,
        "installments": 0,
        "payer": {
            "full_name": "Charles Edward Miller",
            "email": "charles.miller@payments.example.com",
            "cpf": "987.654.321-11",
            "ssn": "412-88-9012",
        },
        "card": {
            "number": "5412-3344-5566-7890",
            "cvv": "319",
        },
        "auth_session": {
            "bearer_token": (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJ1c2VyIjoiY2hhcmxlcy5taWxsZXIiLCJjcGYiOiI5ODcuNjU0LjMyMS0xMSJ9."
                "dummysignature998877"
            ),
        },
    }

    with sentry_sdk.new_scope() as scope:
        _configure_sentry_scope_with_pii(
            scope=scope,
            request=request,
            scenario_slug=scenario_slug,
            user_info={
                "id": "usr_33109",
                "username": "charles.miller",
                "email": "charles.miller@payments.example.com",
                "ip_address": "201.18.74.12",
                "cpf": "987.654.321-11",
                "ssn": "412-88-9012",
            },
            request_payload=payment_payload,
        )
        try:
            calculate_installment_plan(payment_payload)
        except Exception as exc:
            return _capture_and_build_response(exc, scenario_slug, raise_unhandled)

    return JSONResponse(status_code=200, content={"status": "unexpected_success"})


@app.post("/api/scenarios/type-mismatch")
async def trigger_type_mismatch(
    request: Request,
    raise_unhandled: bool = Query(default=False),
) -> JSONResponse:
    """Scenario 3: Trigger TypeError (float + str) in recurring billing with plaintext password & tokens."""
    scenario_slug = "type_mismatch_billing"
    subscription_payload = {
        "subscription_id": "SUB-ENT-7721",
        "base_plan_price": 249.90,
        "gateway_fee_override": "14.90",
        "account": {
            "email": "anna.costa@fintech.io",
            "cpf": "456.789.123-44",
            "ssn": "521-44-7789",
        },
        "credentials": {
            "password": "SuperSecretPassword!2026#Prod",
            "api_secret_key": "api_secret_mock_99aabbccddeeff001122334455",
            "bearer_token": (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJhbm5hLmNvc3RhIiwicm9sZSI6ImFkbWluIn0."
                "secretTokenSignature12345"
            ),
        },
        "billing_card": {
            "number": "3782-822463-10005",
            "cvv": "1042",
        },
    }

    with sentry_sdk.new_scope() as scope:
        _configure_sentry_scope_with_pii(
            scope=scope,
            request=request,
            scenario_slug=scenario_slug,
            user_info={
                "id": "usr_77210",
                "username": "anna.costa",
                "email": "anna.costa@fintech.io",
                "ip_address": "177.92.11.40",
                "cpf": "456.789.123-44",
            },
            request_payload=subscription_payload,
        )
        try:
            process_recurring_charge(subscription_payload)
        except Exception as exc:
            return _capture_and_build_response(exc, scenario_slug, raise_unhandled)

    return JSONResponse(status_code=200, content={"status": "unexpected_success"})


@app.post("/api/scenarios/breadcrumb-flood")
async def trigger_breadcrumb_flood(
    request: Request,
    raise_unhandled: bool = Query(default=False),
) -> JSONResponse:
    """Scenario 4: Trigger multi-frame AttributeError after 35 noisy + PII breadcrumbs."""
    scenario_slug = "breadcrumb_flood_settlement"
    batch_payload = {
        "batch_id": "BATCH-SETTLE-20261117",
        "customer_context": {
            "full_name": "Robert Alexander Vance",
            "email": "robert.vance@corporate.example.com",
            "cpf": "321.654.987-99",
            "ssn": "689-12-3341",
            "bearer_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.robert.secret.jwt",
        },
        "transactions": [
            {
                "tx_id": "TX-990011",
                "amount": 5840.00,
                "card_number": "4111-2222-3333-4444",
                "settlement_code": None,
            }
        ],
    }

    with sentry_sdk.new_scope() as scope:
        _configure_sentry_scope_with_pii(
            scope=scope,
            request=request,
            scenario_slug=scenario_slug,
            user_info={
                "id": "usr_90123",
                "username": "robert.vance",
                "email": "robert.vance@corporate.example.com",
                "ip_address": "189.10.22.105",
                "cpf": "321.654.987-99",
            },
            request_payload=batch_payload,
        )
        try:
            reconcile_settlement_batch(batch_payload)
        except Exception as exc:
            return _capture_and_build_response(exc, scenario_slug, raise_unhandled)

    return JSONResponse(status_code=200, content={"status": "unexpected_success"})
