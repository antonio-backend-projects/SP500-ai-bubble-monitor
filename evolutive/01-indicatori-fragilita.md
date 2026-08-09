# Indicatori di fragilità — cosa manca

## Già in dash (base)
- CAPE Shiller (spesso **stale** se XLS non aggiornato)
- Buffett indicator (CMV / FRED)
- Equity famiglie (FRED Z.1)
- Peso Mag7 / Top10 (Slickcharts)
- Margin debt YoY (oggi spesso **proxy FRED Z.1**, non FINRA)
- Stress concentrazione (derivato)
- S&P vs max 52w

## Mancanze rispetto al piano-strategia

### CAPE
- [ ] CAPE live ~mensile allineato a Shiller/multpl aggiornato (oggi rischio dato 2023 in cache)
- [ ] Badge “as of” evidente sulla card, non solo in footer
- [ ] Confronto CAPE vs mediana / Dot-com / oggi in un solo grafico annotato
- [ ] Forward P/E S&P o PEG come secondo termometro valutazione

### Buffett / market cap vs economia
- [ ] Serie Wilshire / float-adjusted più pulita (Wilshire FRED rimossa nel 2024)
- [ ] Variante “Buffett” con cap S&P+NASDAQ vs GDP
- [ ] Storia lunga sul grafico (non solo finestra corta)

### Equity famiglie
- [ ] Breakdown azioni dirette vs fondi vs pensioni (se disponibile in Z.1)
- [ ] Confronto esplicito con picchi 1960 / 2000 / 2008 / oggi
- [ ] Indicatore “effetto ricchezza” (consumo vs equity wealth) — opzionale macro

### Concentrazione
- [ ] Peso Top10 e Mag7 come **due card distinte** (oggi misti)
- [ ] Herfindahl / effective N d’indice
- [ ] Peso settore Technology + Communication vs storia
- [ ] Contributo Mag7 al return YTD dell’indice

### Leva / margin
- [ ] Debit balances FINRA ufficiali (livello + YoY) senza scrape fragile
- [ ] Credit balances / net liquidity investitori (piano: minimo storico)
- [ ] Separare **livello $** e **YoY** in due score (oggi YoY basso azzera tutto)
- [ ] Disclaimer UI sempre visibile se fonte = proxy Z.1 ≠ FINRA
- [ ] Margin debt / GDP o / market cap (normalizzazione)

### Altri tipici pre-bolla (assenti)
- [ ] IPO / SPACs volume o deal count
- [ ] Retail options volume / call skew estremi
- [ ] AAII / sentiment retail
- [ ] Insider selling net aggregato
- [ ] Valutazioni private (unicorn marks) — difficile, solo proxy news
