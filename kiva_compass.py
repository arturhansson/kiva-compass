"""Kiva Compass 0.1 — rank Kiva loans according to personal impact values."""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fetch_kiva import KivaFetchError, fetch_loans


@dataclass(frozen=True)
class Match:
    label: str
    icon: str
    points: int
    keywords: tuple[str, ...]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_loans(data: Any) -> list[dict[str, Any]]:
    """Accept either a JSON list or an object with a ``loans`` list."""
    loans = data.get("loans") if isinstance(data, dict) else data
    if not isinstance(loans, list):
        raise ValueError("Indata måste vara en JSON-lista eller ett objekt med nyckeln 'loans'.")
    return [loan for loan in loans if isinstance(loan, dict)]


def searchable_text(loan: dict[str, Any]) -> str:
    fields = (
        loan.get("name", ""), loan.get("use", ""), loan.get("description", ""),
        loan.get("sector", ""), loan.get("activity", ""),
    )
    tags = loan.get("tags", [])
    return " ".join(map(str, (*fields, *tags))).casefold()


def score_loan(loan: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    text = searchable_text(loan)
    matches: list[dict[str, Any]] = []

    for rule in config["themes"]:
        keywords = tuple(keyword.casefold() for keyword in rule["keywords"])
        if any(keyword in text for keyword in keywords):
            matches.append({"label": rule["label"], "icon": rule["icon"], "points": rule["points"]})

    attributes = loan.get("attributes", {})
    for rule in config.get("attributes", []):
        actual = attributes.get(rule["field"], loan.get(rule["field"]))
        expected = rule.get("equals", True)
        if actual == expected:
            matches.append({"label": rule["label"], "icon": rule["icon"], "points": rule["points"]})

    positive_score = sum(match["points"] for match in matches if match["points"] >= 0)
    penalties = [match["points"] for match in matches if match["points"] < 0]
    # Several avoidance keywords may describe the same loan. Apply the strongest
    # penalty once, rather than multiplying it for overlapping labels.
    score = positive_score + (min(penalties) if penalties else 0)
    result = dict(loan)
    result.update(score=score, matches=matches)
    return result


def stars(score: int, maximum: int) -> str:
    filled = max(0, min(5, round(5 * score / maximum))) if maximum else 0
    return "★" * filled + "☆" * (5 - filled)


def render_html(results: list[dict[str, Any]], config: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    maximum = sum(max(0, rule["points"]) for group in (config["themes"], config.get("attributes", [])) for rule in group)
    cards = []
    for loan in results:
        reasons = " ".join(
            f'<span class="tag">{html.escape(m["icon"])} {html.escape(m["label"])} +{m["points"]}</span>'
            for m in loan["matches"]
        ) or '<span class="muted">Inga kompassträffar ännu</span>'
        url = html.escape(str(loan.get("url", "#")), quote=True)
        cards.append(f"""
        <article>
          <div class="score">{loan['score']} p · {stars(loan['score'], maximum)}</div>
          <h2><a href="{url}">{html.escape(str(loan.get('name', 'Namnlöst lån')))}</a></h2>
          <p class="place">{html.escape(str(loan.get('country', 'Okänt land')))} · {html.escape(str(loan.get('activity', loan.get('sector', ''))))}</p>
          <p>{html.escape(str(loan.get('use', '')))}</p>
          <div>{reasons}</div>
        </article>""")

    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    document = f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Kiva Compass</title><style>
:root{{--ink:#18352d;--green:#2f7d65;--paper:#f4f1e8;--card:#fffdf7;--gold:#d29b28}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 system-ui,sans-serif}}
main{{max-width:850px;margin:auto;padding:48px 20px}} header{{margin-bottom:32px}} h1{{font-size:clamp(2.2rem,7vw,4.5rem);margin:0;line-height:1}}
.intro,.place,.muted{{color:#587068}} article{{background:var(--card);padding:24px;margin:18px 0;border-radius:14px;border-left:6px solid var(--green);box-shadow:0 3px 16px #17352d14}}
h2{{margin:.15rem 0}} a{{color:var(--ink)}} .score{{color:var(--gold);font-weight:750;letter-spacing:.03em}} .tag{{display:inline-block;background:#dcebe3;border-radius:99px;padding:4px 10px;margin:4px 4px 0 0;font-size:.88rem}}
footer{{margin-top:35px;color:#6b7974;font-size:.85rem}}
</style></head><body><main><header><h1>🧭 Kiva Compass</h1><p class="intro">Lån som ligger nära det du vill hjälpa fram i världen.</p></header>
{''.join(cards)}<footer>Skapad {generated}. Poängen är vägledning, inte en garanti för effekt eller återbetalning.</footer>
</main></body></html>"""
    output.write_text(document, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Poängsätt lån med Kiva Compass.")
    parser.add_argument("--input", type=Path, default=Path("sample_loans.json"))
    parser.add_argument("--config", type=Path, default=Path("compass.json"))
    parser.add_argument("--output", type=Path, default=Path("report.html"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--live", action="store_true", help="Hämta aktuella lån direkt från Kiva")
    parser.add_argument("--pages", type=int, default=1, help="Kiva-sidor att hämta (1–5)")
    args = parser.parse_args()

    try:
        loans = fetch_loans(limit=100, pages=args.pages) if args.live else normalize_loans(load_json(args.input))
        config = load_json(args.config)
        ranked = sorted((score_loan(loan, config) for loan in loans), key=lambda item: (-item["score"], str(item.get("name", ""))))
        render_html(ranked[: args.limit], config, args.output)
    except (OSError, ValueError, KeyError, KivaFetchError, json.JSONDecodeError) as error:
        parser.error(str(error))

    print(f"Kiva Compass: {len(loans)} lån bedömda. Rapport: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
