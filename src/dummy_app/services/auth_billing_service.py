from typing import Any

import sentry_sdk


def process_recurring_charge(subscription_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Process a recurring subscription renewal charge with optional gateway fee override.

    Intentional defect for Auto-Remediation PoC (Scenario 3 - TypeError / Unparsed String):
    `gateway_fee_override` arrives from external webhook/form payload as a string
    (e.g., `"14.90"`) instead of `float`. Adding `base_plan_price + gateway_fee_override`
    triggers `TypeError: unsupported operand type(s) for +: 'float' and 'str'` while
    exposing account password, API key, SSN, CPF, and Bearer token in stack trace vars.
    """
    account = subscription_payload.get("account", {})
    credentials = subscription_payload.get("credentials", {})
    billing_card = subscription_payload.get("billing_card", {})

    account_email = account.get("email", "subscriber@example.com")
    account_cpf = account.get("cpf", "000.000.000-00")
    account_ssn = account.get("ssn", "000-00-0000")
    raw_password = credentials.get("password", "")
    bearer_jwt = credentials.get("bearer_token", "")
    api_secret = credentials.get("api_secret_key", "")
    card_pan = billing_card.get("number", "")

    sentry_sdk.add_breadcrumb(
        category="auth.credentials",
        message=(
            f"Authenticated recurring billing for {account_email} "
            f"with password={raw_password} and token=Bearer {bearer_jwt}"
        ),
        level="debug",
        data={
            "email": account_email,
            "cpf": account_cpf,
            "ssn": account_ssn,
            "password": raw_password,
            "api_secret_key": api_secret,
            "card_pan": card_pan,
        },
    )

    base_plan_price = float(subscription_payload.get("base_plan_price", 99.90))
    gateway_fee_override = subscription_payload.get("gateway_fee_override", 0.0)

    # BUG: gateway_fee_override may be passed as a string (e.g. "14.90") in JSON payload
    total_charge = base_plan_price + gateway_fee_override

    return {
        "account_email": account_email,
        "total_charge": round(total_charge, 2),
    }


def _extract_primary_transaction(
    transactions: list[dict[str, Any]],
    customer_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Innermost helper (Level 3 of call stack) that normalizes the settlement reference code.

    Intentional defect for Auto-Remediation PoC (Scenario 4 - Multi-frame Call Stack & Breadcrumb Flood):
    Calls `.upper()` directly on `primary_tx.get("settlement_code")` which is `None` for
    pending PIX/wire settlements, raising `AttributeError: 'NoneType' object has no attribute 'upper'`.
    """
    primary_tx = transactions[0]
    customer_cpf = customer_context.get("cpf", "")
    customer_email = customer_context.get("email", "")
    raw_settlement_code = primary_tx.get("settlement_code")

    sentry_sdk.add_breadcrumb(
        category="ledger.settlement",
        message=(
            f"Normalizing settlement_code for CPF {customer_cpf} "
            f"({customer_email}) on card {primary_tx.get('card_number')}"
        ),
        level="warning",
        data={
            "customer_cpf": customer_cpf,
            "customer_email": customer_email,
            "card_number": primary_tx.get("card_number"),
            "bearer_token": customer_context.get("bearer_token"),
        },
    )

    # BUG: raw_settlement_code is None when settlement is still pending confirmation
    normalized_code = raw_settlement_code.strip().upper()

    return {
        "transaction_id": primary_tx.get("tx_id"),
        "settlement_code": normalized_code,
        "amount": primary_tx.get("amount", 0.0),
    }


def _audit_customer_entries(
    batch_id: str,
    customer_context: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Intermediate helper (Level 2 of call stack) that generates redundant polling breadcrumbs."""
    for poll_attempt in range(1, 36):
        sentry_sdk.add_breadcrumb(
            category="ledger.polling.noise",
            message=f"[Poll #{poll_attempt}/35] Waiting for bank clearing lock on batch {batch_id}",
            level="debug",
            data={
                "attempt": poll_attempt,
                "batch_id": batch_id,
                "status": "WAITING_LOCK",
            },
        )

    sentry_sdk.add_breadcrumb(
        category="ledger.pii_audit",
        message=(
            f"Auditing batch {batch_id} for {customer_context.get('email')} "
            f"CPF={customer_context.get('cpf')} SSN={customer_context.get('ssn')}"
        ),
        level="info",
        data=customer_context,
    )

    return _extract_primary_transaction(transactions, customer_context)


def reconcile_settlement_batch(batch_payload: dict[str, Any]) -> dict[str, Any]:
    """Entry point (Level 1 of call stack) for batch reconciliation."""
    batch_id = str(batch_payload.get("batch_id", "BATCH-000"))
    customer_context = batch_payload.get("customer_context", {})
    transactions = batch_payload.get("transactions", [])

    return _audit_customer_entries(
        batch_id=batch_id,
        customer_context=customer_context,
        transactions=transactions,
    )
