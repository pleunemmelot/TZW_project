""""
Titel: TZW.py
Auteur: Albert Segers, Asmae , Pleun Emmelot
In opdracht van Nictiz, als project voor vak 2.5 Software Engineering van de BSc Medische Informatiekunde, UvA/Amsterdam UMC
Doel: Omzetten van voorkeurstermen uit Thesaurus Zorg en Welzijn van meervoud naar enkelvoud

Dit is de asynchrone versie, en is niet afgemaakt. Maakt gebruikt van de /batches endpoint maar deze is nog niet geconfigureerd bij de UvA LiteLLM API.
"""
import xml.etree.ElementTree as ET
from openai import OpenAI
from dotenv import load_dotenv
import sys
import json
import csv
import time
import copy
import os

XML_INPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW/xml_test2.xml"
OUTPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW/TZW_project/Output/"
EVMV = "evmv"
MODEL = "gpt-4.1-nano"
SYSTEM_PROMPT = "Je bent een Nederlandse terminologie-checker. Geef altijd antwoord met een JSON object."
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

def r1_jsonl_genereren(concepten: dict) -> str:
    """
    TODO: uitwerken
    """
    jsonl_pad = OUTPUT_PAD + "ronde1.jsonl"
    
    with open(jsonl_pad, "w") as f:
        for pt in concepten:
            json_regel = {
                "custom_id": pt,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role" : "system", "content" : SYSTEM_PROMPT},
                        {"role": "user", "content": f"""
Analyseer deze preferred term (PT) stapsgewijs:

PT: "{pt}"

Stap 1: Is de PT een zelfstandig naamwoord? Zo niet → uitkomstcode 1, stop.
Stap 2: Staat de PT in het meervoud? Zo niet → uitkomstcode 2. Zo ja → uitkomstcode 99.

JSON-formaat:
{{"originele_pt": string, "uitkomstcode": int, "redenering": string}}
"""
                        }],
                    "temperature" : 0
                }
            }
            f.write(json.dumps(json_regel) + "\n")
    
    return jsonl_pad

def r2_jsonl_genereren(concepten: dict) -> str:
    """
    TODO: uitwerken
    """
    jsonl_pad = OUTPUT_PAD + "ronde2.jsonl"
    
    with open(jsonl_pad, "w") as f:
        for pt in concepten:
            concept = concepten[pt]
            evmv_npts = [npt["term"] for npt in concept.get("npts", []) if EVMV in npt.get("adns", [])]
            json_regel = {
                "custom_id": pt,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role" : "system", "content" : SYSTEM_PROMPT},
                        {"role": "user", "content": f"""
Analyseer deze PT en NPT-lijst stapsgewijs:

PT: "{pt}"
NPT's: {evmv_npts}

Stap 1: Filter meervoudige NPT's eruit. Geen enkelvoudige over → uitkomstcode 5, stop.
Stap 2: Kies de enkelvoudige NPT die het meest op de PT lijkt.
Stap 3: Goede vervanging → uitkomstcode 6. Twijfelgeval → uitkomstcode 7.

JSON-formaat:
{{"originele_pt": string, "uitkomstcode": int, "redenering": string, "gekozen_npt": string|null, "evmv_npts": list}}
"""
                        }],
                    "temperature" : 0
                }
            }
            f.write(json.dumps(json_regel) + "\n")
    
    return jsonl_pad

def filter_batch(concepten: dict) -> tuple: 
    """
    TODO: uitwerken
    """
    return 

def post_batch(jsonl_pad: str, ronde: str) -> str:
    """
    TODO: uitwerken
    """
    with open(jsonl_pad, "rb") as f:
        file = client.files.create(file=f, purpose="batch")
    
    batch = client.batches.create(
        input_file_id=file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    print(f"Batch {ronde} ingediend: {batch.id}")
    
    return batch.id

def get_batch(batch_id: str, ronde: str) -> tuple:
    """
    TODO: uitwerken
    """
    while True:
        batch = client.batches.retrieve(batch_id)
        print(f"{ronde} status: {batch.status}, requests: {batch.request_counts}")
        
        if batch.status == "completed":
            break
        if batch.status in ("failed", "cancelled", "expired"):
            sys.exit(f"{ronde} mislukt met status {batch.status}")
        time.sleep(60)
    
    resultaten = {}
    response = client.files.content(batch.output_file_id)
    print(response.text) #Output testen
    
    return resultaten

def batch_handler(concepten: dict) -> tuple:
    """
    TODO: uitwerken, beslissen of loggen in deze functie gebeurt
    """
    #1. jsonl_genereren() voor ronde 1 aanroepen met de dict van alle concepten
    #2. post_batch() voor ronde  1
    #3. get_batch() voor ronde 1, inclusief pollen
    #4. output ronde 1: uitkmomstcode 1 en 2 pt's in resultaten zetten, uitkomstcode 99 pt's meenemen in seleectie
    #5. filter_batch() aanroepen met selectie
    #6. output filter: uitkmomstcode 3 en 4 pt's in resultaten zetten, uitkomstcode 99 pt's meenemen in seleectie
    #7. jsonl_genereren() voor ronde 2 aanroepen met de selectie
    #8. post_batch() voor ronde  2 
    #9. get_batch() voor ronde 2, inclusief pollen
    #10. output ronde 2 in resultaten zetten
    
    resultaten = []
    log_data = [] 
    
    r1_jsonl = r1_jsonl_genereren(concepten)
    r1_batch_id = post_batch(r1_jsonl, "Ronde 1")
    r1_resultaten = get_batch(r1_batch_id, "Ronde 1")
    
    #filter
    
    r2_jsonl = r2_jsonl_genereren() # aanvullen
    r2_batch_id = post_batch(r2_jsonl, "Ronde 2")
    r2_resultaten = get_batch(r2_batch_id, "Ronde 2")
    
    return resultaten, log_data

def log_uitkomst(originele_pt: str, uitkomstcode: int, redenering: str, gekozen_pt: str, evmv_npts: list) -> dict:
    """
    Maakt het een dictionary voor het loggen van de uitkomst
    """
    return {"originele_pt" : originele_pt, "uitkomstcode" : uitkomstcode, "redenering" : redenering, "gekozen_pt" : gekozen_pt, "evmv_npts" : evmv_npts}

def pt_selectie(originele_pt: str, evmv_npts: list) -> tuple:
    return

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

def batch_omzetten(batch: dict) -> tuple:
    """
    Zet voor een batch concepten de PT van meervoud naar enkelvoud, waar dit mogelijk is. 
    Geeft als output een batch omgezette concepten als dictionary en een batch log data als een list van dictionaries
    """
    omgezet = {}
    log_data = []
    
    for originele_pt, pt_met_npts in batch.items():
        evmv_npts = [npt for npt in pt_met_npts["npts"] if EVMV in npt["adns"]]
        evmv_npts_namen = [npt["term"] for npt in evmv_npts]
        gekozen_pt, uitkomstcode, redenering = pt_selectie(originele_pt, evmv_npts_namen)
        
        if uitkomstcode in (1, 2, 3, 4, 5):
            log_data.append(log_uitkomst(originele_pt, uitkomstcode, redenering, "", evmv_npts_namen)) 
            omgezet[originele_pt] = pt_met_npts
            
        elif uitkomstcode in (6, 7):
            log_data.append(log_uitkomst(originele_pt, uitkomstcode, redenering, gekozen_pt, evmv_npts_namen)) 
            omgezet[gekozen_pt] = term_omzetten(originele_pt, gekozen_pt, pt_met_npts)
            
    return omgezet, log_data

def output_bouwen():
    """
    TODO: uitwerken
    """
    return

def genereer_txt(input_data, output_pad):
    """
    TODO: uitwerken
    """
    return
    
def genereer_log(log_data):
    """
    TODO: uitwerken
    """
    return

def main():
    tree = xml_inlezen(XML_INPUT_PAD)
    concepten = groeperen(tree)
    
    batch_handler(concepten)

if __name__ == "__main__":
    main()
