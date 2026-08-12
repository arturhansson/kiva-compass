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

    new_country_rule = config.get("new_country_bonus")
    if new_country_rule and loan.get("country") in new_country_rule.get("countries", []):
        matches.append({
            "label": new_country_rule["label"],
            "icon": new_country_rule["icon"],
            "points": new_country_rule["points"],
        })

    positive_score = sum(match["points"] for match in matches if match["points"] >= 0)
    penalties = [match["points"] for match in matches if match["points"] < 0]
    # Several avoidance keywords may describe the same loan. Apply the strongest
    # penalty once, rather than multiplying it for overlapping labels.
    score = positive_score + (min(penalties) if penalties else 0)
    result = dict(loan)
    result.update(score=score, matches=matches)
    return result


def stars(score: int, maximum: int) -> str:
    """Map Compass points to fixed, understandable quality bands."""
    del maximum  # Kept in the signature for backwards compatibility.
    if score <= 0:
        filled = 0
    elif score <= 5:
        filled = 1
    elif score <= 9:
        filled = 2
    elif score <= 14:
        filled = 3
    elif score <= 19:
        filled = 4
    else:
        filled = 5
    return "★" * filled + "☆" * (5 - filled)


def render_html(results: list[dict[str, Any]], config: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    maximum = 20
    countries = sorted({str(loan.get("country", "Okänt land")) for loan in results})
    sectors = sorted({str(loan.get("sector", "")) for loan in results if loan.get("sector")})
    activities = sorted({str(loan.get("activity", "")) for loan in results if loan.get("activity")})
    match_labels = sorted({m["label"] for loan in results for m in loan["matches"]})

    def options(values: list[str]) -> str:
        return "".join(f'<option value="{html.escape(value, quote=True)}">{html.escape(value)}</option>' for value in values)

    cards = []
    for loan in results:
        reasons = " ".join(
            f'<span class="tag{" new-country" if m["label"] == "NYTT LAND" else ""}">'
            f'{html.escape(m["icon"])} {html.escape(m["label"])} '
            f'{m["points"]:+d}</span>'
            for m in loan["matches"]
        ) or '<span class="muted">Inga kompassträffar ännu</span>'
        url = html.escape(str(loan.get("url", "#")), quote=True)
        country = str(loan.get("country", "Okänt land"))
        sector = str(loan.get("sector", ""))
        activity = str(loan.get("activity", sector))
        labels = "|".join(m["label"] for m in loan["matches"])
        cards.append(f"""
        <article data-score="{loan['score']}" data-country="{html.escape(country, quote=True)}"
          data-sector="{html.escape(sector, quote=True)}" data-activity="{html.escape(activity, quote=True)}"
          data-labels="{html.escape(labels, quote=True)}">
          <div class="card-head"><h2><a href="{url}">{html.escape(str(loan.get('name', 'Namnlöst lån')))}</a></h2>
          <div class="score">{loan['score']} p · {stars(loan['score'], maximum)}</div></div>
          <p class="place">{html.escape(country)} · {html.escape(activity)}</p>
          <p class="purpose">{html.escape(str(loan.get('use', '')))}</p>
          <div class="tags">{reasons}</div>
        </article>""")

    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    document = f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Kiva Compass</title><style>
:root{{--ink:#18352d;--green:#2f7d65;--paper:#f4f1e8;--card:#fffdf7;--gold:#d29b28}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.38 system-ui,sans-serif}}
main{{max-width:1080px;margin:auto;padding:20px 16px 36px}} header{{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}}
h1{{font-size:clamp(1.8rem,5vw,2.8rem);margin:0;line-height:1}} .intro{{margin:.3rem 0 0}} .intro,.place,.muted{{color:#587068}}
.balance-box{{background:var(--ink);color:white;padding:9px 12px;border-radius:10px;min-width:225px}} .balance-box label{{font-weight:700}}
.balance-box input{{width:82px;margin-left:6px;padding:5px;border:0;border-radius:6px;font:inherit}} #slots{{display:block;font-size:.82rem;margin-top:3px;color:#dcebe3}}
.controls{{position:sticky;top:0;z-index:2;display:grid;grid-template-columns:2fr repeat(5,minmax(105px,1fr));gap:7px;background:#e8e4d8;padding:10px;border-radius:11px;margin-bottom:10px;box-shadow:0 3px 12px #17352d18}}
.controls input,.controls select{{min-width:0;width:100%;padding:7px;border:1px solid #b9c2bd;border-radius:7px;background:white;color:var(--ink);font:inherit}}
.summary{{grid-column:1/-1;display:flex;justify-content:space-between;color:#587068;font-size:.82rem}} .legend{{white-space:nowrap}}
#loans{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}} article{{background:var(--card);padding:13px 14px;margin:0;border-radius:10px;border-left:4px solid var(--green);box-shadow:0 2px 9px #17352d12}}
.card-head{{display:flex;align-items:baseline;justify-content:space-between;gap:10px}} h2{{font-size:1.08rem;margin:0}} a{{color:var(--ink)}} .score{{color:#9a6b08;font-weight:800;white-space:nowrap}} .place{{margin:2px 0 5px;font-size:.82rem}} .purpose{{margin:0 0 6px}}
.tag{{display:inline-block;background:#dcebe3;border-radius:99px;padding:2px 7px;margin:2px 2px 0 0;font-size:.72rem}} .new-country{{background:#ffe49a;color:#593d00;font-weight:800;border:1px solid #d29b28}}
footer{{margin-top:22px;color:#6b7974;font-size:.76rem}} [hidden]{{display:none!important}}
@media(max-width:800px){{header{{align-items:start;flex-direction:column}}.controls{{grid-template-columns:repeat(2,1fr)}}#loans{{grid-template-columns:1fr}}.balance-box{{width:100%}}}}
</style></head><body><main><header><div><h1>🧭 Kiva Compass</h1><p class="intro">Hitta lånen som bäst matchar din kompass.</p></div>
<div class="balance-box"><label for="balance">Tillgängligt saldo $</label><input id="balance" type="number" min="0" step="1" placeholder="—"><span id="slots">Sparas endast i den här webbläsaren</span></div></header>
<section class="controls" aria-label="Filtrera lån">
<input id="search" type="search" placeholder="Sök namn, land eller ändamål…">
<select id="theme"><option value="">Alla Compass-kategorier</option>{options(match_labels)}</select>
<select id="country"><option value="">Alla länder</option>{options(countries)}</select>
<select id="sector"><option value="">Alla sektorer</option>{options(sectors)}</select>
<select id="activity"><option value="">Alla aktiviteter</option>{options(activities)}</select>
<select id="minscore"><option value="-999">Alla poäng</option><option value="1">Minst 1 p</option><option value="10">Minst 10 p</option><option value="15">Minst 15 p</option><option value="20">Minst 20 p</option></select>
<div class="summary"><span id="count"></span><span class="legend">★ 1–5 · ★★ 6–9 · ★★★ 10–14 · ★★★★ 15–19 · ★★★★★ 20+</span></div>
</section><section id="loans">{''.join(cards)}</section>
<footer>Skapad {generated}. Poäng och stjärnor är vägledning, inte en garanti för effekt eller återbetalning.</footer>
<script>
const cards=[...document.querySelectorAll('article')];
const fields=['search','theme','country','sector','activity','minscore'];
function filterLoans(){{
 const q=document.querySelector('#search').value.toLowerCase();
 const theme=document.querySelector('#theme').value, country=document.querySelector('#country').value;
 const sector=document.querySelector('#sector').value, activity=document.querySelector('#activity').value;
 const minscore=Number(document.querySelector('#minscore').value); let visible=0;
 cards.forEach(card=>{{const ok=(!q||card.innerText.toLowerCase().includes(q))&&(!theme||card.dataset.labels.split('|').includes(theme))&&(!country||card.dataset.country===country)&&(!sector||card.dataset.sector===sector)&&(!activity||card.dataset.activity===activity)&&Number(card.dataset.score)>=minscore; card.hidden=!ok;if(ok)visible++;}});
 document.querySelector('#count').textContent=`${{visible}} av ${{cards.length}} lån visas`;
}}
fields.forEach(id=>document.querySelector('#'+id).addEventListener('input',filterLoans)); filterLoans();
const balance=document.querySelector('#balance'), slots=document.querySelector('#slots');
const saved=localStorage.getItem('kivaCompassBalance'); if(saved!==null) balance.value=saved;
function updateBalance(){{const value=Number(balance.value); if(balance.value===''){{slots.textContent='Sparas endast i den här webbläsaren';return;}} localStorage.setItem('kivaCompassBalance',String(value)); const loans=Math.floor(value/25), left=value-loans*25; slots.textContent=`Räcker till ${{loans}} lån à $25 · $${{left.toFixed(0)}} kvar`;}}
balance.addEventListener('input',updateBalance); updateBalance();
</script></main></body></html>"""
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
