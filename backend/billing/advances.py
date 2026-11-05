"""
Advance payments (H4): money a patient deposits before bills exist, then
adjusted against invoices or refunded.

Every movement is an AdvanceTransaction and moves AdvanceAccount.balance with
the account row locked, so two requests cannot spend the same money. When an
invoice is involved its row is locked first, then the account (the same
order everywhere, so concurrent requests cannot deadlock). Adjusting against
an invoice records an ordinary Payment with method "Advance", so invoice
balances, status and reports need no special case.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .services import ZERO, _locked, money, net_paid, new_reference, record_payment, record_refund

ADVANCE_METHOD = "Advance"


def _user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _positive(amount):
    amount = money(amount)
    if amount <= ZERO:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    return amount


def _locked_account(hospital_id, patient_id, create=False):
    from .models import AdvanceAccount

    if create:
        AdvanceAccount.objects.get_or_create(hospital_id=hospital_id, patient_id=patient_id)
    account = AdvanceAccount.objects.select_for_update().filter(hospital_id=hospital_id, patient_id=patient_id).first()
    if account is None:
        raise ValidationError({"advance": "This patient has no advance at this hospital."})
    return account


def _move(account, kind, amount, user, **fields):
    from .models import AdvanceTransaction

    sign = 1 if kind in (AdvanceTransaction.Kind.DEPOSIT, AdvanceTransaction.Kind.RETURNED) else -1
    account.balance = money(account.balance + sign * amount)
    if account.balance < ZERO:
        raise ValidationError({"amount": "Not enough advance balance."})
    account.save(update_fields=["balance", "updated_at"])
    prefix = {"deposit": "ADV", "refund": "ADVR"}.get(kind, "ADVA")
    return AdvanceTransaction.objects.create(
        account=account, kind=kind, amount=amount, balance_after=account.balance,
        receipt_number=new_reference(prefix), created_by=_user(user), **fields,
    )


def _existing(account, idempotency_key):
    if not idempotency_key:
        return None
    return account.transactions.filter(idempotency_key=idempotency_key).first()


@transaction.atomic
def record_deposit(hospital_id, patient_id, amount, method="Cash", user=None, idempotency_key="", reference=""):
    """Money received in advance. Re-sending the same key returns the first deposit."""
    from .models import AdvanceTransaction

    if (method or "").strip() == ADVANCE_METHOD:
        raise ValidationError({"payment_method": "Choose how the money was received."})
    account = _locked_account(hospital_id, patient_id, create=True)
    existing = _existing(account, idempotency_key)
    if existing:
        return existing, False
    return _move(account, AdvanceTransaction.Kind.DEPOSIT, _positive(amount), user,
                 payment_method=method or "Cash", idempotency_key=idempotency_key or "",
                 reference=(reference or "")[:200]), True


@transaction.atomic
def apply_to_invoice(invoice, amount, user=None, idempotency_key=""):
    """Adjust advance money against an invoice, up to both its balance and the advance balance."""
    from .models import AdvanceTransaction

    invoice = _locked(invoice)
    account = _locked_account(invoice.hospital_id, invoice.patient_id)
    existing = _existing(account, idempotency_key)
    if existing:
        return existing, False
    amount = _positive(amount)
    if amount > account.balance:
        raise ValidationError({"amount": f"Amount exceeds the advance balance ({account.balance})."})
    # record_payment re-checks the invoice balance and cancellation under the same lock.
    payment, _ = record_payment(invoice, amount, method=ADVANCE_METHOD, user=user, _from_advance=True)
    return _move(account, AdvanceTransaction.Kind.APPLIED, amount, user, payment_method=ADVANCE_METHOD,
                 idempotency_key=idempotency_key or "", invoice=invoice, payment=payment), True


def applied_to_invoice(invoice):
    """Advance money still sitting on ``invoice``: applied minus returned."""
    from .models import AdvanceTransaction

    total = ZERO
    for row in AdvanceTransaction.objects.filter(invoice=invoice).values("kind", "amount"):
        total += row["amount"] if row["kind"] == AdvanceTransaction.Kind.APPLIED else -row["amount"]
    return money(total)


@transaction.atomic
def return_to_advance(invoice, amount, reason, user=None):
    """Refund part of an invoice back into the patient's advance instead of cash."""
    from .models import AdvanceTransaction

    invoice = _locked(invoice)
    account = _locked_account(invoice.hospital_id, invoice.patient_id)
    amount = _positive(amount)
    returnable = min(applied_to_invoice(invoice), net_paid(invoice))
    if amount > returnable:
        raise ValidationError({"amount": f"Only advance money can go back to the advance ({returnable})."})
    refund = record_refund(invoice, amount, reason, method=ADVANCE_METHOD, user=user, _from_advance=True)
    move = _move(account, AdvanceTransaction.Kind.RETURNED, amount, user, payment_method=ADVANCE_METHOD,
                 invoice=invoice, payment=refund, reference=(reason or "").strip()[:200])
    return refund, move


@transaction.atomic
def refund_to_patient(account, amount, reason, method="Cash", user=None):
    """Pay unused advance back to the patient."""
    from .models import AdvanceTransaction

    if not (reason or "").strip():
        raise ValidationError({"reason": "A refund reason is required."})
    if (method or "").strip() == ADVANCE_METHOD:
        raise ValidationError({"payment_method": "Choose how the money is paid back."})
    account = _locked_account(account.hospital_id, account.patient_id)
    amount = _positive(amount)
    if amount > account.balance:
        raise ValidationError({"amount": f"Refund exceeds the advance balance ({account.balance})."})
    return _move(account, AdvanceTransaction.Kind.REFUND, amount, user, payment_method=method or "Cash",
                 reference=reason.strip()[:200])
