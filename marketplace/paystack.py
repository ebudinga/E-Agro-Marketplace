"""Thin Paystack API client. Docs: https://paystack.com/docs/api/"""
import hmac
import hashlib
import requests
from django.conf import settings

PAYSTACK_API = "https://api.paystack.co"


def _headers():
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(email, amount_kobo, reference, callback_url,
                           subaccount=None, transaction_charge=None,
                           metadata=None, bearer="account"):
    payload = {
        "email": email,
        "amount": int(amount_kobo),
        "reference": reference,
        "callback_url": callback_url,
        "bearer": bearer,
        "metadata": metadata or {},
    }
    if subaccount:
        payload["subaccount"] = subaccount
    if transaction_charge is not None:
        payload["transaction_charge"] = int(transaction_charge)

    resp = requests.post(
        f"{PAYSTACK_API}/transaction/initialize",
        json=payload, headers=_headers(), timeout=20,
    )
    data = resp.json()
    if not data.get("status"):
        raise Exception(f"Paystack init failed: {data.get('message', 'unknown error')}")
    return data["data"]


def verify_transaction(reference):
    resp = requests.get(
        f"{PAYSTACK_API}/transaction/verify/{reference}",
        headers=_headers(), timeout=20,
    )
    data = resp.json()
    if not data.get("status"):
        raise Exception(f"Paystack verify failed: {data.get('message', 'unknown error')}")
    return data["data"]


def create_subaccount(business_name, settlement_bank, account_number, percentage_charge):
    payload = {
        "business_name": business_name,
        "settlement_bank": settlement_bank,
        "account_number": account_number,
        "percentage_charge": float(percentage_charge),
    }
    resp = requests.post(
        f"{PAYSTACK_API}/subaccount",
        json=payload, headers=_headers(), timeout=20,
    )
    data = resp.json()
    if not data.get("status"):
        raise Exception(f"Subaccount creation failed: {data.get('message', 'unknown error')}")
    return data["data"]


def list_banks(country="nigeria"):
    try:
        resp = requests.get(
            f"{PAYSTACK_API}/bank?country={country}&perPage=200",
            headers=_headers(), timeout=20,
        )
        return resp.json().get("data", [])
    except Exception:
        return []


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)