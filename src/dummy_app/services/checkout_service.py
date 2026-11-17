from typing import Any

import sentry_sdk


def apply_promotional_discount(order_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate the final checkout total after applying a promotional coupon.

    Intentional defect for Auto-Remediation PoC (Scenario 1 - KeyError / NoneType):
    Assumes `order_payload["discount"]` is always a populated dictionary with a
    `"percentage"` key. When a customer checks out without a coupon (`"discount": None`),
    this raises `TypeError: 'NoneType' object is not subscriptable` while holding
    customer PII in local variables and breadcrumbs.
    """
    customer = order_payload.get("customer", {})
    payment_card = order_payload.get("payment_card", {})
    customer_email = customer.get("email", "unknown@example.com")
    customer_cpf = customer.get("cpf", "000.000.000-00")
    card_number = payment_card.get("number", "0000-0000-0000-0000")
    card_cvv = payment_card.get("cvv", "000")

    sentry_sdk.add_breadcrumb(
        category="checkout.validation",
        message=f"Validating checkout cart for customer CPF {customer_cpf} ({customer_email})",
        level="info",
        data={
            "customer_cpf": customer_cpf,
            "customer_email": customer_email,
            "card_pan": card_number,
            "card_cvv": card_cvv,
        },
    )

    subtotal = float(order_payload.get("subtotal", 0.0))
    discount_block = order_payload["discount"]

    # BUG: discount_block can be None when no coupon is applied by the user
    discount_percentage = float(discount_block["percentage"])
    discount_amount = round(subtotal * (discount_percentage / 100.0), 2)
    final_total = round(subtotal - discount_amount, 2)

    return {
        "customer_email": customer_email,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "final_total": final_total,
    }


def calculate_installment_plan(payment_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Compute per-installment charges and gateway fees for credit card checkout.

    Intentional defect for Auto-Remediation PoC (Scenario 2 - ZeroDivisionError):
    Does not validate `installments <= 0` before dividing `net_amount / installments`.
    When a one-click payment payload sends `installments = 0`, it raises
    `ZeroDivisionError` with credit card, CPF, SSN, and auth token in local scope.
    """
    payer = payment_payload.get("payer", {})
    card_data = payment_payload.get("card", {})
    auth_session = payment_payload.get("auth_session", {})

    payer_name = payer.get("full_name", "Anonymous Buyer")
    payer_cpf = payer.get("cpf", "000.000.000-00")
    payer_ssn = payer.get("ssn", "000-00-0000")
    payer_email = payer.get("email", "buyer@example.com")
    raw_credit_card = card_data.get("number", "0000-0000-0000-0000")
    bearer_token = auth_session.get("bearer_token", "")

    sentry_sdk.add_breadcrumb(
        category="payment.gateway",
        message=(
            f"Preparing installment schedule for {payer_name} "
            f"(CPF={payer_cpf}, SSN={payer_ssn}, Card={raw_credit_card})"
        ),
        level="info",
        data={
            "authorization": f"Bearer {bearer_token}",
            "payer_email": payer_email,
            "payer_cpf": payer_cpf,
        },
    )

    gross_amount = float(payment_payload.get("amount", 0.0))
    cashback_credit = float(payment_payload.get("cashback_credit", 0.0))
    installments_count = int(payment_payload.get("installments", 1))

    net_amount = gross_amount - cashback_credit

    # BUG: installments_count is 0 when client sends a single-payment order as 0 installments
    installment_value = round(net_amount / installments_count, 2)

    return {
        "payer_email": payer_email,
        "net_amount": net_amount,
        "installments": installments_count,
        "installment_value": installment_value,
    }
