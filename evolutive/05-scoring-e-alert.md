# Scoring e alert — cosa manca / da ritoccare

## Problema già osservato
Con seed (CAPE 41.9 + margin YoY 51%) → **TARDA BOLLA**.  
Con live (CAPE stale 33 + margin Z.1 YoY 2%) → **RISCHIO CONTENUTO**, anche con Buffett 219% e famiglie 45%+.

Il mercato non è “migliorato”: è cambiato il **mix dati + pesi**.

## Fix prioritari

### Alert banner
- [ ] Regola: se Buffett ≥ fuoco **e** household ≥ Dot-com → almeno **TARDA BOLLA / VIGILANZA**, anche se media fragilità < 70
- [ ] Alert basato su `max(score medio, score dei pezzi estremi)` o quorum (2+ indicatori rossi)
- [ ] Mostrare sotto al banner: “N indicatori fragilità in zona estrema”

### Pesi fragilità
- [ ] Ridurre peso `margin_debt` quando fonte = proxy Z.1
- [ ] Oppure score margin su **livello** + YoY (blend), non solo YoY
- [ ] CAPE stale: abbassare peso o escludere dalla media con flag

### Score mancanti sulle card
- [ ] Dare score a `S&P vs max 52w` e `Mag7 variazione media` (oggi “score —”)
- [ ] Includere under-surface stress nel composito (oggi spesso solo display)

### Trasparenza
- [ ] Pannello “come è calcolato” con pesi attuali da `settings.json`
- [ ] Toggle “scenario piano” (usa seed/reference) vs “live only”
- [ ] Diff vs run precedente: Δ fragilità / Δ innesco

### Calibrazione
- [ ] Tabella soglie documentata (perché 350 bp, 200% Buffett, ecc.)
- [ ] Test di regressione: input piano-strategia → regime “Tarda bolla” obbligatorio
- [ ] Sensitivity: ±10% su un input non deve flippare il banner senza motivo
