# TZW-AI project

## 1. Projectbeschrijving

De Thesaurus Zorg en Welzijn (TZW), beheerd door Nictiz, bevat 56.000+ termen gebruikt in het sociaal domein. Conform de nieuwe standaard NL-SBB moeten voorkeurstermen (PT's) van meervoud naar enkelvoud worden omgezet. Vanwege de omvang vereist dit geautomatiseerde tooling met behulp van AI.

## 2. Bestanden

`tzw.py`: verwerkt batches synchroon via `chat.completions.create` en is volledig bruikbaar. 
`tzw_asynchroon.py`: verwerkt JSONL-bestanden asynchroon via de `/batches` endpoint. Deze versie is niet afgemaakt omdat dit endpoint nog niet geconfigureerd is in de UvA LiteLLM API.

## 3. Gebruik

- Maak een `.env` bestand aan met `UVA_API_KEY=<jouw_sleutel>`
- Pas in `tzw.py` de constanten `XML_INPUT_PAD` en `OUTPUT_PAD` aan
- Run: `python tzw.py`

**Testbestand aanmaken:** Een eenvoudige manier om een testbestand te maken is om de XML met alle codes te kopiëren en hierin te zoeken (Ctrl + F) op <DESCRIPTOR> (kan in VS Code). Rechtsboven zie je staan op welke descriptor je staat. Als je bijvoorbeeld wil testen met 100 concepten, ga je naar de 100e descriptor, en selecteer vanaf de `<CONCEPT`> van de eerst volgende term tot aan het einde van het bestand. Verwijder dit, behalve de `</THESAURUS>`, en sla op. Je hebt nu een testbestand met 100 PT's.

## 4. Input en Output

### Input

Een XML-bestand in het TZW-thesaurusformaat. Elk concept heeft de structuur:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<!-- Report : REPORT GENERATOR -->
<!-- Created: 4-3-2026 11:37:38 -->
<!DOCTYPE THESAURUS [
<!ELEMENT THESAURUS (CONCEPT+)>
<!ELEMENT CONCEPT ( (DESCRIPTOR|NON-DESCRIPTOR),UF*,USE*,GUID*,TNR*,ADM*,ADN*)>
<!ELEMENT DESCRIPTOR (#PCDATA)>
<!ELEMENT NON-DESCRIPTOR (#PCDATA)>
<!ELEMENT UF (#PCDATA)>
<!ELEMENT USE (#PCDATA)>
<!ELEMENT GUID (#PCDATA)>
<!ELEMENT TNR (#PCDATA)>
<!ELEMENT ADM (#PCDATA)>
<!ELEMENT ADN (#PCDATA)>
]>

<THESAURUS>

<CONCEPT>
 <NON-DESCRIPTOR>farma industrie</NON-DESCRIPTOR>
 <USE>farmaceutische industrieën</USE>
 <GUID>{9B10EAB7-BF51-447D-933C-FC7446BEFA68}</GUID>
 <TNR>67901</TNR>
 <ADM>AA</ADM>
 <ADM>syn</ADM>
 <ADN>dubbel</ADN>
 <ADN>foutspel</ADN>
 <ADN>zonderkoppelteken</ADN>

<CONCEPT>
 <DESCRIPTOR>farmaceutische industrieën</DESCRIPTOR>
 <UF>farma industrie</UF>
 <UF>farmabedrijf</UF>
 <UF>farmabedrijven</UF>
 <UF>farmaceut</UF>
 <UF>farmaceuten</UF>
 <UF>farmaceutisch bedrijf</UF>
 <UF>farmaceutische bedrijven</UF>
 <UF>farmaceutische industrieen</UF>
 <UF>farmaceutische industrieën</UF>
 <UF>farma-industrie</UF>
 <UF>geneesmiddelenfabrikant</UF>
 <UF>geneesmiddelenfabrikanten</UF>
 <UF>geneesmiddelenindustrie</UF>
 <UF>geneesmiddelenindustrieen</UF>
 <UF>geneesmiddelenindustrieën</UF>
 <UF>geneesmiddelfabrikant</UF>
 <UF>geneesmiddelfabrikanten</UF>
 <UF>geneesmiddelindustrie</UF>
 <UF>geneesmiddelindustrieen</UF>
 <UF>geneesmiddelindustrieën</UF>
 <GUID>{46BFC3AA-7250-4A9F-B99D-4389FA632017}</GUID>
 <TNR>6079</TNR>
 <ADM>AA</ADM>
 <ADM>nictizaangeleverd</ADM>
 <ADM>syn</ADM>
</CONCEPT>
```

Relevante codes:
- `DESCRIPTOR` : Preferred Term (PT)
- `NON-DESCRIPTOR` — Non Preferred Term (NPT)
- `ADN: evmv` — NPT is de enkelvoudsvorm van een meervoud PT
- `ADN: foutspel` — spelfout

### Output

`log.csv`: CSV per PT: originele term, uitkomstcode, redenering van de LLM, gekozen nieuwe PT, alle evmv-NPT's

`dict_output.json`: JSON Tussenresultaat: de volledige geparsede dictionary na XML-inlezen 

`output.txt`: Omgezette thesaurus in het TZW-invoerformaat

De CSV bevat de volgende uitkomstcodes:

| Code | Betekenis | Verwerking |
|---|---|---|
| 1 | Geen gekoppelde evmv-NPT's | Python-filter, PT ongewijzigd |
| 2 | Alle evmv-NPT's hebben een foutspelcode | Python-filter, PT ongewijzigd |
| 3 | PT is geen zelfstandig naamwoord | LLM stap 1, PT ongewijzigd |
| 4 | PT staat al in het enkelvoud | LLM stap 2, PT ongewijzigd |
| 5 | Alle evmv-NPT's (zonder foutspel) staan in het meervoud | LLM stap 3, PT ongewijzigd |
| 6 | Twijfelgeval; nieuwe PT gekozen | LLM stap 4+5, PT omgezet |
| 7 | Succes; nieuwe PT gekozen | LLM stap 4+5, PT omgezet |

Bij omzetting (codes 6 en 7) worden de volgende bewerkingen uitgevoerd:
- `term` van de PT → nieuwe enkelvoudsvorm
- Originele meervoudsvorm toegevoegd aan `UF` van de PT (op de plek van de nieuwe PT)
- `USE` van alle NPT's → nieuwe PT
- `evmv`-code verwijderd van alle NPT's

## 5. Pipeline

### Selectieflowchart

![Flowchart PT selectie](TZW_project/Flowchart_PT_selectie_v2.png)

### Beschrijving
Stap 1\. De volledige XML wordt ingelezen en geparsed naar een python Dictionary. 

- Geparsed met bijbehorende codes:  
  -  DESCRIPTOR (Preferred Term (PT)) of NON-DESCRIPTOR (Non-Preferred Term (NPT))  
  - Overige codes (ADM, ADN, etc.)  
- De input XML staat op alfabetische volgorde. Na parsing zijn concepten gegroepeerd op basis van PT met gekoppelde NPT’s. 

Stap 2\. De dictionary wordt opgedeeld in batches van X grootte voor verwerking door de AI.

Stap 3\. De batches worden omgezet volgens dit proces:

- De AI loopt bovenstaande flowchart door. Als er succes is (er is wordt omgezet):   
  - DESCRIPTOR en NON-DESCRIPTOR worden omgewisseld:  
  - De UF van de gekozen evmv-tag wordt omgewisseld, originele PT komt op de plek van de nieuwe PT  
  - Voor de NPT’s: alle USE worden de nieuwe PT  
  - Evmv weghalen  
  - Overige codes veranderen NIET  
- Verder wordt per PT de uitkomst gelogd naar een csv bestand

Stap 5\. Output TXT genereren

## 6. Opmerkingen voor verdere ontwikkeling

De flow is nog niet definitief. Er zijn verschillende ideeën over hoe dit het beste kan worden aangepakt. Dit kan in de toekomst in samenspraak met Nictiz verder worden uitgewerkt. Een aantal suggesties: 
- In de functie flow_handler() kan de volgorde van de stappen worden aangepast. 
- Een lllm_stapX() functie kan relatief eenvoudig worden gekopieerd om een extra stap toe te voegen. 
- De prompts (inclusief de system prompt), de temperature en het AI model kunnen worden aangepast om de uitkomsten verder te finetunen.

Nu wordt gebruik gemaakt van de UvA API. Deze zal moeten worden vervangen door een alternatief vanuit nictiz, of er zal een andere aanpak moeten worden uitgewerkt die compatibel is met ChatGPT Enterprise.

Overgebleven ‘evmv’ codes moeten worden omgedraaid. Dus ‘evmv’ moet bij de ADN van alle meervoudsvormen van de enkelvoud PT. Dit is nog niet in de code verwerkt.

Het is nog niet helemaal duidelijk of er nog meer concept specifieke codes zijn die meegegeven moeten worden in geval van omzetting (‘foutspel’ bijvoorbeeld).

Er kan nog een check worden toegevoegd bij het ophalen van elke response, waarbij wordt nagegaan of de AI geen termen geeft overgeslagen.

### Links

**UVA LiteLLM API:** https://llmproxy.uva.nl/
**OpenAI API Docs:** https://developers.openai.com/api/docs 