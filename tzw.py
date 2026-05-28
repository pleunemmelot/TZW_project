""""
Titel: TZW.py
Auteurs: Albert Segers, Pleun Emmelot, Asmae Talbi
In opdracht van Nictiz, als project voor vak 2.5 Software Engineering van de BSc Medische Informatiekunde, UvA/Amsterdam UMC
Doel: Omzetten van voorkeurstermen uit Thesaurus Zorg en Welzijn van meervoud naar enkelvoud
"""
import xml.etree.ElementTree as ET
from openai import OpenAI
from dotenv import load_dotenv
import sys
import json
import csv
import copy
import os

XML_INPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW/xml_test2.xml"
OUTPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW/TZW_project/Output/"
EVMV = "evmv"
MODEL = "gpt-4.1"
SYSTEM_PROMPT = "Je bent een Nederlandse terminologie-checker. Geef altijd antwoord met een JSON object."
BATCH_GROOTTE = 20

DESCRIPTOR_CODES = [
    "UF", "ADM", "RT", "RUB", "BT", "NT", "INV", "GUID", "TNR", "SN",
    "NICTIZ", "BRN", "KNKINV", "SNOFSN", "SNOSCTID", "CLOSESNO", "SNOFSNNL",
    "ZINL", "SNB", "OPM", "ZIRUB", "TDZ", "BRNSNB", "GEB", "NIER", "SNOOPM",
    "ADN", "REUMA", "INVTDZ", "KNKSN", "PVT", "SNNIER", "NVD", "HIS", "MYLEX",
    "NPCF", "AFKVOL", "IKNL", "LCA", "LCC", "KNKRUB", "PLEEG", "ZISNIS",
    "DIAB", "TEL", "PARK", "TOEL", "BRNTDZ", "NB", "PZNL", "IGJSN", "HERZIEN",
    "MS", "ZIOPM", "HISTORY", "MOD", "KNKOPM", "ZICAT", "PalliaPT", "TDZOPM",
    "ZISNKIKV", "BRNDEFTDZJUR", "DEFTDZJUR", "ZIBRN", "ZIBRNSN", "REUMAOPM",
    "TDZTOEL", "BRNIS"
]
NON_DESCRIPTOR_CODES = [
    "ADM", "ADN", "INV", "USE", "GUID", "TNR", "MEE", "RUB", "KNKINV", "SN",
    "NIER", "NPCF", "ZINL", "REUMA", "IKNL", "AFKVOL", "MYLEX", "KNKRUB",
    "PLEEG", "TDZ", "DIAB", "BRN", "PARK", "ZIRUB", "OPM", "INVTDZ", "MS",
    "NICTIZ", "HISTORY", "MOD", "UFSNOFSN", "UFSNOSCTID", "UFSNOFSNNL",
    "KNKSN", "GEB", "NVD", "SNOOPM", "KNKOPM", "LCA", "LCC", "TOEL", "NB",
    "ZISNIS", "ZIOPM", "HERZIEN", "ZICAT", "BRNTDZ", "HIS", "IGJSN", "PZNL",
    "TDZOPM", "BRNSNB", "SNB", "BRNDEFTDZJUR", "DEFTDZJUR", "SNNIER", "TEL",
    "ZIBRN", "ZISNKIKV",
]

load_dotenv()

client = OpenAI(
    base_url="https://llmproxy.uva.nl/",
    api_key=os.getenv("UVA_API_KEY"),
)

def get_code(concept, code: str) -> list:
    """
    Haalt codes op uit XML structuur, List van code(s) als output
    """
    return [element.text for element in concept.findall(code) if element.text is not None]

def xml_inlezen(xml_pad: str):
    """
    Leest XML in, geeft een Tree van de XML als output
    """
    try:
        tree = ET.parse(xml_pad)
    except FileNotFoundError:
        sys.exit(f"Kan bestand '{xml_pad}' niet vinden")
    except ET.ParseError as e:
        sys.exit(f"XML kan niet worden geparsed: {e}")
    return tree
    
def groeperen(tree) -> dict:
    """   
    Groepeert alle concepten uit de XML op basis van Preferred Terms (PT's) en gekoppelde Non-Preferred Terms (NPT's), 
    geeft als output een Dictionary met PT's en gekoppelde NPT's en een JSON
    """  
    root = tree.getroot()
    alle_concepten = root.findall("CONCEPT")
    
    descriptors = {}
    non_descriptors = []
    
    for concept in alle_concepten:
        desc = concept.find("DESCRIPTOR")
        non_desc = concept.find("NON-DESCRIPTOR")
        
        if desc is not None and desc.text: 
            term = desc.text
            concept_data = {"term": term}
            concept_data.update({code.lower() + "s": get_code(concept, code) for code in DESCRIPTOR_CODES})
            descriptors[term] = concept_data
            
        elif non_desc is not None and non_desc.text:
            term = non_desc.text
            concept_data = {"term": term}
            concept_data.update({code.lower() + "s": get_code(concept, code) for code in NON_DESCRIPTOR_CODES})
            non_descriptors.append(concept_data)
            
    groep_dict = {}
    for pt, data in descriptors.items():
        groep_dict[pt] = {"pt": data, "npts": []}
    
    ongekoppeld = 0
    for npt in non_descriptors:
        pt_ref = npt["uses"][0]
        if pt_ref in groep_dict:
            groep_dict[pt_ref]["npts"].append(npt)
        else:
            ongekoppeld += 1
    
    print(f"{len(groep_dict)} PT's ingelezen")
    print(f"{len(non_descriptors)} NPT's ingelezen")
    print(f"{ongekoppeld} NPT's niet gekoppeld")
    
    #JSON genereren
    with open(OUTPUT_PAD + "dict_output.json", "w") as f:
        json.dump(groep_dict, f)
    
    return groep_dict

def batch_maken(groep_dict: dict, batch_grootte: int) -> list:
    """
    Maakt batches van gegroepeerde concepten. Geeft een List van Dictionairies als output
    """
    items = list(groep_dict.items())
    batches = []
    for i in range(0, len(items), batch_grootte):
        batch = dict(items[i : i + batch_grootte])
        batches.append(batch)
    print(f"{len(batches)} batches gemaakt")    
    
    return batches

def log_uitkomst(originele_pt: str, uitkomstcode: int, redenering: str, gekozen_pt: str, evmv_npts: list) -> dict:
    """
    Maakt het een dictionary voor het loggen van de uitkomst
    """
    return {"PT" : originele_pt, "uitkomstcode" : uitkomstcode, "redenering" : redenering, "gekozen_pt" : gekozen_pt, "evmv_npts" : evmv_npts}

def evmv_filter(batch: dict) -> tuple:
    """
    Filtert alle NPT's zonder gekoppelde 'evmv' codes en met 'foutspelcode' uit de selectie.
    Geen gekoppelde NPT's --> 
    """
    afgehandeld = []
    doorgeven = []
    
    for originele_pt, pt_met_npts in batch.items():
        evmv_npts = [npt for npt in pt_met_npts["npts"] if EVMV in npt.get("adns", [])]
        geldige_npts = [npt for npt in evmv_npts if "foutspel" not in npt.get("adns", [])]
        
        if not evmv_npts:
            afgehandeld.append(log_uitkomst(originele_pt, 1, "Geen gekoppelde evmv NPT's", "",  []))
        
        elif not geldige_npts:
            afgehandeld.append(log_uitkomst(originele_pt, 2, "Alle evmv NPT's hebben een foutspel code", "", []))
        
        else:
            doorgeven.append(originele_pt)
            
    return afgehandeld, doorgeven

def llm_stap1(actief: list) -> tuple:
    """
    Stap 1: Beoordeel of de originele PT een zelfstandig naamwoord is.
    Enkelvoud → uitkomstcode 3.
    Meervoud → doorgeven aan stap 2.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role" : "system", "content" : SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Analyseer deze lijst van preferred terms (PT's).
Beoordeel voor elke PT of het een zelfstandig naamwoord is.
Als het geen zelfstandig naamwoord is -> uitkomstcode 3.
Als het wel een zelfstandig naamwoord is -> uitkomstcode 99.

Input PT's: {json.dumps(actief)}

Geef antwoord EXACT in het volgende JSON-formaat:
{{
  "PT": {{"uitkomstcode": int, "redenering": "string"}},
  ...
}}
"""
            }],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    resultaten = json.loads(response.choices[0].message.content)
    
    afgehandeld = []
    doorgeven = []
    for pt, data in resultaten.items():
        if data.get("uitkomstcode") == 3:
            afgehandeld.append(log_uitkomst(pt, 3, data.get("redenering"), "", []))
        else:
            doorgeven.append(pt)
    
    return afgehandeld, doorgeven

def llm_stap2(actief: list) -> tuple:
    """
    Stap 2: Beoordeel of de originele PT enkelvoud of meervoud is.
    Enkelvoud → uitkomstcode 4.
    Meervoud → doorgeven aan stap 3.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Analyseer deze lijst van preferred terms (PT's).
Beoordeel voor elke PT of het enkelvoud of meervoud is.
Als het enkelvoud is -> uitkomstcode 4.
Als het meervoud is -> uitkomstcode 99.

Input PT's: {json.dumps(actief)}

Geef antwoord EXACT in het volgende JSON-formaat:
{{
  "PT": {{"uitkomstcode": int, "redenering": "string"}},
  ...
}}
"""}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    resultaten = json.loads(response.choices[0].message.content)

    afgehandeld = []
    doorgeven = []
    for pt, data in resultaten.items():
        if data.get("uitkomstcode") == 4:
            afgehandeld.append(log_uitkomst(pt, 4, data.get("redenering"), "", []))
        else:
            doorgeven.append(pt)

    return afgehandeld, doorgeven

def llm_stap3(actief: list, evmv_npts_per_pt: dict) -> tuple:
    """
    Stap 3: Filter evmv NPT's die in het meervoud staan.
    Als er na filtering geen evmv NPT's meer over zijn -> uitkomstcode 5.
    Anders doorgeven aan stap 4 en 5.
    """
    input_data = {
        pt: [npt["term"] for npt in evmv_npts_per_pt.get(pt, [])]
        for pt in actief
    }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Voor elke preferred term (PT) is een lijst van gekoppelde evmv-NPT's gegeven.
Beoordeel voor elke NPT of het meervoud is. Geef alleen de NPT's terug die ENKELVOUD zijn.
Als er voor een PT geen enkelvoud NPT's overblijven, geef dan een lege lijst.

Input: {json.dumps(input_data)}

Geef antwoord EXACT in het volgende JSON-formaat:
{{
  "PT": {{
    "enkelvoud_npts": ["term1", "term2"],
    "redenering": "string"
  }},
  ...
}}
"""}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    resultaten = json.loads(response.choices[0].message.content)

    afgehandeld = []
    doorgeven = []
    evmv_npts_gefilterd = {}

    for pt, data in resultaten.items():
        enkelvoud_npts = data.get("enkelvoud_npts", [])
        npt_objecten = [
            npt for npt in evmv_npts_per_pt.get(pt, [])
            if npt["term"] in enkelvoud_npts
        ]

        if not npt_objecten:
            afgehandeld.append(log_uitkomst(pt, 5, data.get("redenering"), "", []))
        else:
            doorgeven.append(pt)
            evmv_npts_gefilterd[pt] = npt_objecten

    return afgehandeld, doorgeven, evmv_npts_gefilterd

def llm_stap4_5(actief: list, evmv_npts_gefilterd: dict) -> list:
    """
    Stap 4+5: Rank de evmv NPT's op gelijkenis met de originele PT,
    selecteer nr. 1, beoordeel of het een twijfelgeval is.
    Twijfelgeval → uitkomstcode 6, anders → uitkomstcode 7.
    """
    input_data = {
        pt: [npt["term"] for npt in evmv_npts_gefilterd.get(pt, [])]
        for pt in actief
    }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Voor elke preferred term (PT) is een lijst van kandidaat-enkelvoudstermen gegeven.
Rangschik de kandidaten op gelijkenis met de PT (meest gelijkend eerst).
Selecteer de beste kandidaat (nr. 1).
Beoordeel of je zeker bent van de keuze:
- Als je zeker bent -> uitkomstcode 7
- Als het een twijfelgeval is -> uitkomstcode 6

Input: {json.dumps(input_data)}

Geef antwoord EXACT in het volgende JSON-formaat:
{{
  "PT": {{
    "gekozen_npt": "string",
    "uitkomstcode": int,
    "redenering": "string",
    "gerankte_npts": ["term1", "term2", ...]
  }},
  ...
}}
"""}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    resultaten = json.loads(response.choices[0].message.content)

    afgehandeld = []
    for pt, data in resultaten.items():
        gekozen_npt = data.get("gekozen_npt")
        uitkomstcode = data.get("uitkomstcode")
        alle_npts = [npt["term"] for npt in evmv_npts_gefilterd.get(pt, [])]
        afgehandeld.append(log_uitkomst(pt, uitkomstcode, data.get("redenering"), gekozen_npt, alle_npts))

    return afgehandeld

def flow_handler(batch: dict) -> list:
    """
    Loodst een batch van concepten door alle stappen heen. Geeft een list met alle resultaten 
    """
    resultaten = []

    # Filter PT's zonder evmv NPT's en 'foutspel' codes
    afgehandeld, filter_actief = evmv_filter(batch)
    resultaten.extend(afgehandeld)

    if not filter_actief:
        return resultaten

    # Stap 1: zelfstandig naamwoord?
    afgehandeld, stap1_actief = llm_stap1(filter_actief)
    resultaten.extend(afgehandeld)

    if not stap1_actief:
        return resultaten

    # Stap 2: enkelvoud of meervoud?
    afgehandeld, stap2_actief = llm_stap2(stap1_actief)
    resultaten.extend(afgehandeld)

    if not stap2_actief:
        return resultaten

    evmv_npts_per_pt = {}
    for pt in stap2_actief:
        pt_met_npts = batch.get(pt, {})
        evmv_npts_per_pt[pt] = [
            npt for npt in pt_met_npts.get("npts", [])
            if EVMV in npt.get("adns", [])
            and "foutspel" not in npt.get("adns", [])
        ]

    # Stap 3: filter meervoud NPT's
    afgehandeld, stap3_actief, evmv_npts_gefilterd = llm_stap3(stap2_actief, evmv_npts_per_pt)
    resultaten.extend(afgehandeld)

    if not stap3_actief:
        return resultaten

    # Stap 4+5: ranken + twijfelgeval beoordelen
    afgehandeld = llm_stap4_5(stap3_actief, evmv_npts_gefilterd)
    resultaten.extend(afgehandeld)

    return resultaten

def term_omzetten(originele_pt: str, gekozen_pt: str, pt_met_npts: dict) -> dict:
    """
    Voert alle bewerkingen uit wanneer een term wordt omgezet
    TODO: Uitvragen bij Nictiz welke verdere bewerkingen er nodig zijn (bijvoorbeeld wat doen bij een originele PT met foutspel code)
    """
    pt_met_npts_omgezet = copy.deepcopy(pt_met_npts)
            
    # PT bewerkingen: "term" van "pt" → gekozen_pt, Voor UF van gekozen_pt → originele_pt
    pt_met_npts_omgezet["pt"]["term"] = gekozen_pt
    if gekozen_pt in pt_met_npts_omgezet["pt"]["ufs"]:
        i = pt_met_npts_omgezet["pt"]["ufs"].index(gekozen_pt)
        pt_met_npts_omgezet["pt"]["ufs"][i] = originele_pt
    else:
        pt_met_npts_omgezet["pt"]["ufs"].append(originele_pt)
    
    # NPT bewerkingen: USE van alle NPT's → gekozen_pt, evmv code verwijderen van alle NPT's, gekozen PT omzetten naar de originele PT
    for npt in pt_met_npts_omgezet["npts"]:
        npt["uses"] = [gekozen_pt]
        if EVMV in npt["adns"]:
            npt["adns"].remove(EVMV)
        
        if npt["term"] == gekozen_pt:
            npt["term"] = originele_pt
            
        #TODO: EVMV codes toevoegen aan NPT's
    
    return pt_met_npts_omgezet

def concepten_omzetten(concepten: dict, resulaten: list) -> dict:
    """
    Zet voor alle concepten de PT van meervoud naar enkelvoud, waar dit mogelijk is. 
    Geeft als output een batch omgezette concepten als dictionary.
    """
    omgezet = copy.deepcopy(concepten)
    
    for regel in resulaten:
        uitkomstcode = regel.get("uitkomstcode")
        
        if uitkomstcode in (1, 2, 3, 4, 5):
            continue
            
        elif uitkomstcode in (6, 7):
            originele_pt = regel.get("PT")
            gekozen_pt = regel.get("gekozen_pt")
            pt_met_npts = omgezet[originele_pt]
            
            omgezet[gekozen_pt] = term_omzetten(originele_pt, gekozen_pt, pt_met_npts)
            
            omgezet[gekozen_pt] = term_omzetten(originele_pt, gekozen_pt, pt_met_npts)
            if originele_pt != gekozen_pt and originele_pt in omgezet:
                del omgezet[originele_pt]
            
    return omgezet

def output_bouwen(omgezet: dict) -> list:
    """
    Bouwt een lijst van tekstblokken op basis van de omgezette concepten.
    """
    blokken = []
 
    for pt_met_npts in omgezet.values():
        pt_data = pt_met_npts["pt"]
 
        # PT blok
        regels = [pt_data["term"]]
        for code in DESCRIPTOR_CODES:
            for waarde in pt_data.get(code.lower() + "s", []):
                regels.append(f"{code}: {waarde}")
        blokken.append("\n".join(regels))
 
        # NPT blokken
        for npt in pt_met_npts["npts"]:
            regels = [npt["term"]]
            for code in NON_DESCRIPTOR_CODES:
                for waarde in npt.get(code.lower() + "s", []):
                    regels.append(f"{code}: {waarde}")
            blokken.append("\n".join(regels))
 
    return blokken

def genereer_txt(blokken: list, output_pad: str) -> None:
    """
    Schrijft de lijst van blokken naar output.txt.
    """
    with open(output_pad + "output.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(blokken))
    
def genereer_log(resulaten) -> None:
    """
    Genereert een csv bestand met de resultaten.
    """
    with open(OUTPUT_PAD + "log.csv", "w", newline="") as csvfile:
        fieldnames = ["PT", "uitkomstcode", "redenering", "gekozen_pt", "evmv_npts"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resulaten)
        
def main():
    """
    Roept alle functies in de juiste volgorde aan.
    """
    # Voorbewerking
    tree = xml_inlezen(XML_INPUT_PAD)
    concepten = groeperen(tree)
    batches = batch_maken(concepten, BATCH_GROOTTE)
    
    # Verwerking
    totaal_resultaten = []
    aantal = 0
    for batch in batches:
        totaal_resultaten.extend(flow_handler(batch))
        aantal += 1
        print(f"{aantal} batch(es) verwerkt")
    
    # Resultaten genereren
    genereer_log(totaal_resultaten)
    omgezet = concepten_omzetten(concepten, totaal_resultaten)
    
    output = output_bouwen(omgezet)
    genereer_txt(output, OUTPUT_PAD)
    
if __name__ == "__main__":
    main()
