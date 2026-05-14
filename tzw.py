""""
Titel: TZW.py
Auteur: Albert Segers 
In opdracht van Nictiz, als project voor vak 2.5 Software Engineering van de BSc Medische Informatiekunde, UvA/Amsterdam UMC
Doel: Omzetten van voorkeurstermen uit Thesaurus Zorg en Welzijn van meervoud naar enkelvoud
"""
import xml.etree.ElementTree as ET
import sys
import json
import csv
import copy

XML_INPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW_project/testbestand_xml.xml"
OUTPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW_project/"
BATCH_GROOTTE = 100
EVMV = "evmv"
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

def log_uitkomst(originele_pt: str, uitkomstcode: int, gekozen_pt: str, evmv_npts: list) -> dict:
    """
    Maakt het een dictionary voor het loggen van de uitkomst
    """
    return {"originele_pt" : originele_pt, "uitkomst" : uitkomstcode, "gekozen_pt" : gekozen_pt, "evmv_termen" : evmv_npts}

def pt_selectie(originele_pt_term: str, evmv_npts: list) -> tuple:
    """
    Selecteert nieuwe Preferred Term (PT) op basis van evmv code(s).
    TODO: Vervangen door AI API call
    Geeft als output een uitkomstcode en een eventuele gekozen PT
    Uitkomstodes:
        
    """
    if len(evmv_npts) == 0: #Controle of er evmv-termen aanwezig zijn 
        uitkomstcode = 1    #Uitkomstcode 1: Geen evmv NPT(s) bij PT
        return "", uitkomstcode
    
    else:
        uitkomstcode = 7
    
        return evmv_npts[0]["term"], uitkomstcode

def term_omzetten(originele_pt_term: str, gekozen_pt_term: str, pt_met_npts: dict) -> dict:
    """
    Voert alle bewerkingen uit wanneer een term wordt omgezet
    TODO: Uitvragen bij Nictiz welke verdere bewerkingen er nodig zijn (bijvoorbeeld wat doen bij een originele PT met foutspel code)
    """
    pt_met_npts_omgezet = copy.deepcopy(pt_met_npts)
            
    # PT bewerkingen: "term" van "pt" → gekozen_pt_term, Voor UF van gekozen_pt_term → originele_pt_term
    pt_met_npts_omgezet["pt"]["term"] = gekozen_pt_term
    i = pt_met_npts_omgezet["pt"]["ufs"].index(gekozen_pt_term)
    pt_met_npts_omgezet["pt"]["ufs"][i] = originele_pt_term
    
    # NPT bewerkingen: USE van alle NPT's → gekozen_pt_term, evmv code verwijderen van alle NPT's, gekozen PT omzetten naar de originele PT
    for npt in pt_met_npts_omgezet["npts"]:
        npt["uses"] = [gekozen_pt_term]
        if EVMV in npt["adns"]:
            npt["adns"].remove(EVMV)
        
        if npt["term"] == gekozen_pt_term:
            npt["term"] = originele_pt_term
            
        #TODO: EVMV codes toevoegen aan NPT's
    
    return pt_met_npts_omgezet

def batch_omzetten(batch: dict) -> tuple:
    """
    Zet voor een batch concepten de PT van meervoud naar enkelvoud, waar dit mogelijk is. 
    Geeft als output een batch omgezette concepten als dictionary en een batch log data als een list van dictionaries
    """
    omgezet = {}
    log_data = []
    
    for originele_pt_term, pt_met_npts in batch.items():
        evmv_npts = [npt for npt in pt_met_npts["npts"] if EVMV in npt["adns"]]
        evmv_npts_termen = [npt["term"] for npt in evmv_npts]
        gekozen_pt_term, uitkomstcode = pt_selectie(originele_pt_term, evmv_npts)
        
        if uitkomstcode in (1, 2, 3, 4, 5, 6):
            log_data.append(log_uitkomst(originele_pt_term, uitkomstcode, "", evmv_npts_termen))
            omgezet[originele_pt_term] = pt_met_npts
            
        elif uitkomstcode == 7:
            log_data.append(log_uitkomst(originele_pt_term, uitkomstcode, gekozen_pt_term, evmv_npts_termen))
            omgezet[gekozen_pt_term] = term_omzetten(originele_pt_term, gekozen_pt_term, pt_met_npts)
            
    return omgezet, log_data

def output_bouwen():
    return

def genereer_txt(input_data, output_pad):
    return
    
def genereer_log():
    return

def main():
    tree = xml_inlezen(XML_INPUT_PAD)
    concepten = groeperen(tree)
    batches = batch_maken(concepten, BATCH_GROOTTE)


if __name__ == "__main__":
    main()
