# Overdracht – TZW-AI project

## 1. Projectbeschrijving

De Thesaurus Zorg en Welzijn (TZW), beheerd door Nictiz, bevat 56.000+ termen die gebruikt worden in het sociaal domein. Momenteel zijn de voorkeurstermen (PT's) in het meervoud opgenomen. Conform de nieuwe standaard NL-SBB moeten deze worden omgezet naar enkelvoud. Dit vereist geautomatiseerde tooling vanwege de omvang.

### Structuur van de thesaurus
- Een **PT (Preferred Term)** is de voorkeursterm van een concept.
- Een **NPT (Non-Preferred Term)** verwijst via `USE` naar een PT.
- Termen kunnen codes bevatten, o.a.:
  - `ADN: evmv` → deze NPT is de enkelvoudsvorm van een meervouds-PT
  - `UF` → "Used For", staat bij de PT en verwijst naar alle NPT's
  - `ADM`, `GUID`, `TNR`, etc. → administratieve codes die **ongewijzigd** blijven

![img](<../Flowchart PT selectie.png>)

### Relevante datastructuur (Python dict na XML-inlezen)
```python
{
  "farmaceutische industrieën": {
    "pt": {
      "term": "farmaceutische industrieën",
      "ufs": ["farmabedrijf", "farmaceutische industrie", ...],
      "guids": [...],
      "tnrs": [...],
      ...
    },
    "npts": [
      {
        "term": "farmaceutische industrie",
        "adns": ["dubbel", "evmv"],
        "uses": ["farmaceutische industrieën"],
        ...
      },
      ...
    ]
  }
}
```

### Input/output van de thesaurussoftware
- **Input**: UTF-8 `.txt`-bestand in een specifiek formaat (term, codes, dubbele enter tussen termen)
- **Output**: XML

---

## 2. Functionaliteit van `batch_omzetten()`

`batch_omzetten(batch: dict) -> tuple` verwerkt een batch van PT's en hun NPT's en geeft terug:
- `omgezet`: dict van (al dan niet gewijzigde) concepten
- `log_data`: list van log-dictionaries per concept

**Per concept:**
1. Zoek alle NPT's met `ADN: evmv` → dit zijn kandidaten voor de nieuwe PT
2. Roep `pt_selectie(originele_pt_term, evmv_npts)` aan → geeft `(gekozen_pt_term, uitkomstcode)`
3. Bij uitkomstcode 1–6: concept ongewijzigd toevoegen aan `omgezet`, loggen
4. Bij uitkomstcode 7: `term_omzetten()` aanroepen en resultaat toevoegen aan `omgezet`, loggen

### `term_omzetten(originele_pt_term, gekozen_pt_term, pt_met_npts) -> dict`
Voert de volgende bewerkingen uit op een deepcopy:
1. `pt["term"]` → `gekozen_pt_term`
2. In `pt["ufs"]`: `gekozen_pt_term` vervangen door `originele_pt_term`
3. Per NPT: `uses` → `[gekozen_pt_term]`, `evmv` verwijderen uit `adns`
4. De NPT waarvan `term == gekozen_pt_term`: `term` → `originele_pt_term`
