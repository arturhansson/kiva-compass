# Kiva Compass 0.1

Kiva Compass rangordnar lån utifrån teman som cyklar, vatten, sanitet, ren energi,
återbruk och egenmakt. Alla regler finns öppet i `compass.json` och kan ändras utan
programmering.

Lån i ett land som ännu inte finns i Arturs Kiva-statistik får bonusen **Nytt
land**. Listan uppdateras i `new_country_bonus.countries` efter att ett nytt land
har nåtts.

Webbrapporten visar de 100 högst rankade lånen i en kompakt tvåkolumnsvy. Den
kan filtreras på fritext, Compass-kategori, land, sektor, aktivitet och minsta
poäng. Ett frivilligt saldofält sparas endast lokalt i webbläsaren och räknar ut
hur många hela lån à $25 saldot räcker till; saldot publiceras inte på GitHub.

## Kör på Windows

Python 3 krävs. Öppna PowerShell i mappen och kör:

```powershell
python kiva_compass.py
```

Öppna därefter `report.html`. Standardkörningen använder fyra tydligt påhittade
exempellån; de är testdata och ska inte förväxlas med aktuella Kiva-lån.

Hämta 100 aktuella lån direkt från Kiva och visa de 20 högst rankade:

```powershell
python kiva_compass.py --live
```

För ett bredare urval (högst fem sidor):

```powershell
python kiva_compass.py --live --pages 5 --limit 30
```

För en egen JSON-fil:

```powershell
python kiva_compass.py --input mina_lan.json --output min_rapport.html
```

Indata kan vara en lista med lån eller `{ "loans": [...] }`. Fälten `name`,
`country`, `activity`, `use`, `description`, `tags`, `url` och `attributes` stöds.

## Datakälla

Live-läget använder det GraphQL-gränssnitt som Kivas egen lånesida använder. Det
kräver ingen inloggning och gör inga ändringar på Kiva. Om Kiva förändrar sitt
gränssnitt ger programmet ett tydligt fel och exempeldata fortsätter fungera.

## Kör automatiskt på GitHub

Projektet innehåller ett färdigt GitHub Actions-arbetsflöde som testar Compass,
hämtar upp till 500 aktuella lån och publicerar de 40 högst rankade via GitHub
Pages varje morgon. Följ den lugna steg-för-steg-guiden i `GITHUB_GUIDE.md` när
du vill lägga upp projektet. Inga kontouppgifter eller Kiva-lösenord behövs.
