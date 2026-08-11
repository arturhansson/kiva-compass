# GitHub för Kiva Compass – utan förkunskaper

## Vad GitHub gör här

GitHub lagrar en kopia av projektet. GitHub Actions är en tillfällig dator som
startas på ett schema, kör Compass och stängs av igen. GitHub Pages visar den
skapade rapporten som en vanlig webbsida som går att öppna från telefonen.

Arbetsdatorn behöver alltså inte vara på när den dagliga körningen sker.

## Orden som är bra att känna till

- **Repository**: projektmappen på GitHub.
- **Commit**: en sparad version av projektet.
- **Push**: skicka lokala commits till GitHub.
- **Action**: en automatiserad körning.
- **Pages**: webbplats som publiceras från projektet.

## Första publiceringen

1. Skapa ett kostnadsfritt konto på https://github.com om du inte redan har ett.
2. Skapa ett nytt repository, exempelvis `kiva-compass`. Välj **Public** om
   rapporten får vara synlig för alla; välj annars **Private** och kontrollera
   vilka Pages-möjligheter som ingår i ditt GitHub-konto.
3. Anslut den här lokala mappen till repositoryt och skicka filerna dit.
4. Öppna **Settings → Pages** i repositoryt och välj **GitHub Actions** under
   *Build and deployment*.
5. Öppna **Actions → Uppdatera Kiva Compass → Run workflow**.

När körningen är klar visas adressen till rapporten i GitHub. Därefter körs den
automatiskt varje morgon enligt `.github/workflows/kiva-compass.yml`.

## Integritet

Rapporten innehåller endast publika låneuppgifter från Kiva och dina allmänna
poängregler. Lägg inte Kiva-lösenord, betalningsuppgifter eller andra hemligheter
i projektfilerna. Compass behöver inga sådana uppgifter för att skapa rapporten.
