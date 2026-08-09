# Storico e backtest — cosa manca

Oggi la dash è quasi tutta **spot + poche serie**. Manca il confronto storico che il piano usa per ragionare.

## Idee

### Snapshot storici
- [ ] Preset “oggi vs Dot-com peak vs 2007 vs 2021”
- [ ] Tabella indicatori affiancati (CAPE, Buffett, margin, HY, Mag7 weight)
- [ ] Slider temporale se abbiamo cache mensile accumulata

### Archivio locale
- [ ] Job che salva `bubble_state_YYYYMMDD.json` ogni run
- [ ] Grafico prossimità / fragilità / innesco nel tempo (da archivio)
- [ ] Diff settimanale automatico

### Backtest leggero (offline)
- [ ] Regole alert su dati storici FRED (HY, curva, CAPE ricostruito)
- [ ] Misura: quanti mesi prima del peak 2000/2007 l’alert sarebbe scattato
- [ ] **Non** promettere predizione; solo “come si sarebbe comportato il framework”

### Scenario engine
- [ ] Input manuali “what if HY → 450 bp” → ricalcolo score in UI (senza refetch)
- [ ] Preset shock: Fed +100 bp, earnings miss Mag7, recession 40%
