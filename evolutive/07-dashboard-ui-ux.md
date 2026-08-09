# Dashboard UI/UX — cosa manca

## Già fatto
- Alert hero, KPI, radar/gauge, card semaforo
- Grafici CAPE / HY / curva / Buffett / recessione
- Under-surface + watch + news
- Pulsante **Guida** con popup su ogni card

## Gap UX

### Chiarezza dello stato
- [ ] Badge fonte per card (`FRED API`, `seed`, `proxy Z.1`, `stale`)
- [ ] Colore/icona “dato vecchio” se `as_of` > soglia
- [ ] Tooltip soglie direttamente sul valore

### Guide
- [ ] Guide anche su KPI top (Prossimità / Fragilità / Innesco / News)
- [ ] Guide su grafici (cosa significa una linea di soglia)
- [ ] Link “Apri nel piano-strategia” sezione correlata
- [ ] Contenuti guida spostabili in `evolutive/` o `docs/guides/` per edit senza toccare HTML

### Layout
- [ ] Ancora / indici sezione (salta a Fragilità / Innesco / Under)
- [ ] Compact mode mobile più aggressivo
- [ ] Nascondere grafici vuoti invece di canvas vuoti
- [ ] Sticky alert su scroll (opzionale)

### Interazione
- [ ] Espandi card per vedere history sparkline
- [ ] Copia link deep `#card=cape`
- [ ] Export PNG della vista alert (share)

### Accessibilità
- [ ] Focus trap nel modal guida
- [ ] `aria-*` completi, contrasto WCAG
- [ ] Riduzione motion se `prefers-reduced-motion`
