"""Read current fundraising loans from Kiva's public marketplace GraphQL API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = "https://marketplace-api.k1.kiva.org/graphql"
QUERY = """query CompassLoans($limit: Int, $page: Int) {
  fundraisingLoans(limit: $limit, pageNumber: $page) {
    totalCount
    values {
      id name use description gender tags loanAmount status
      activity { name }
      sector { name }
      geocode { city country { name } }
      loanFundraisingInfo { fundedAmount isExpiringSoon }
    }
  }
}"""


class KivaFetchError(RuntimeError):
    pass


def _post(variables: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": QUERY, "variables": variables}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Kiva-Compass/0.2"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise KivaFetchError(f"Kiva kunde inte nås: {error}") from error
    if payload.get("errors"):
        message = payload["errors"][0].get("message", "okänt GraphQL-fel")
        raise KivaFetchError(f"Kiva svarade med ett fel: {message}")
    return payload["data"]["fundraisingLoans"]


def _normalize(item: dict[str, Any]) -> dict[str, Any]:
    tags = [str(tag) for tag in (item.get("tags") or [])]
    tag_text = " ".join(tags).casefold()
    geocode = item.get("geocode") or {}
    country = geocode.get("country") or {}
    fundraising = item.get("loanFundraisingInfo") or {}
    gender = str(item.get("gender", "")).casefold()
    return {
        "id": item["id"],
        "name": item.get("name", "Namnlöst lån"),
        "country": country.get("name", "Okänt land"),
        "city": geocode.get("city"),
        "activity": (item.get("activity") or {}).get("name", ""),
        "sector": (item.get("sector") or {}).get("name", ""),
        "use": item.get("use", ""),
        "description": item.get("description", ""),
        "tags": tags,
        "loan_amount": item.get("loanAmount"),
        "funded_amount": fundraising.get("fundedAmount"),
        "expiring_soon": fundraising.get("isExpiringSoon", False),
        "url": f"https://www.kiva.org/lend/{item['id']}",
        "attributes": {
            "woman_owned": gender in {"female", "woman", "women"},
            "refugee": "refugee" in tag_text or "idp" in tag_text,
            "rural": "rural" in tag_text,
            "first_time_borrower": "first time" in tag_text or "first-time" in tag_text,
        },
    }


def fetch_loans(limit: int = 100, pages: int = 1) -> list[dict[str, Any]]:
    """Fetch up to ``limit`` loans per page from Kiva (maximum five pages)."""
    if not 1 <= limit <= 100:
        raise ValueError("Antalet lån per sida måste vara 1–100.")
    if not 1 <= pages <= 5:
        raise ValueError("Antalet sidor måste vara 1–5.")
    loans: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        result = _post({"limit": limit, "page": page})
        loans.extend(_normalize(item) for item in (result.get("values") or []))
        if len(loans) >= int(result.get("totalCount", 0)):
            break
    return loans
