import xml.etree.ElementTree as ET
import sys
import json
import csv
import copy

XML_INPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW_project/testbestand_xml_v2.xml"
OUTPUT_PAD = "/Users/as/Downloads/MI_25-26/2.5/TZW_project/"
BATCH_GROOTTE = 100
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
    TODO: Geen lege lists opslaan
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
    return {"originele_pt" : originele_pt, "uitkomst" : uitkomstcode, "gekozen_pt" : gekozen_pt, "evmv_termen" : evmv_npts}

def pt_selectie(evmv_npts: list) -> tuple:
    """
    Selecteert nieuwe Preferred Term (PT) op basis van evmv code(s).
    TODO: Vervangen door AI API call
    Geeft als output een uitkomstcode en een eventuele gekozen PT
    Uitkomstodes:
        1. Geen evmv NPT(s) bij PT
        2. PT is geen zelfstandig naamwoord
        3. PT staat al in het enkelvoud
        4. Alle EVMV NPT's hebben een foutspel code
        5. Succes, nieuwe PT gekozen
    """
    if len(evmv_npts) == 0: #Controle of er evmv-termen aanwezig zijn 
        uitkomstcode = 1    #Uitkomstcode 1: Geen evmv NPT(s) bij PT
        return "", uitkomstcode
    
    else:
        uitkomstcode = 5
    
        return evmv_npts[0]["term"], uitkomstcode

def batch_omzetten(batch: dict) -> tuple:
    """
    Zet voor een batch concepten de PT van meervoud naar enkelvoud, waar dit mogelijk is. 
    Geeft als output een batch omgezette concepten als een list van dictionaries en een batch log data als een list van dictionaries
    TODO: Uitkomstcode sectie 5 afmaken en versimpelen
    """
    omgezet = []
    log_data = []
    
    for pt_term, pt_met_npts in batch.items():
        pt_data = pt_met_npts["pt"]         #PT met codes
        npts_data = pt_met_npts["npts"]     #Lijst van NPT's met codes
        evmv_npts = [npt for npt in npts_data if "evmv" in npt["adns"]]
        gekozen_pt_term, uitkomstcode = pt_selectie(evmv_npts)
        
        if uitkomstcode in (1, 2, 3, 4):
            log_data.append(log_uitkomst(pt_term, uitkomstcode, "", []))
            omgezet.append(pt_met_npts)
            
        elif uitkomstcode == 5:
            log_data.append(log_uitkomst(pt_term, uitkomstcode, gekozen_pt_term, [npt["term"] for npt in evmv_npts]))
            pt_met_npts_omgezet = copy.deepcopy(pt_met_npts)
            
            # 1. pt_term vervangen door gekozen_pt_term 
            # TODO: gekozen pt in de NPT's list vervangen door oude PT 
            # 2. UF: gekozen_pt_term → pt_term
            # TODO: 3. USE van alle NPT's → gekozen_pt_term
            # TODO: 4. evmv code verwijderen van de NPT die nu PT wordt
            
            pt_met_npts_omgezet["pt"]["term"] = gekozen_pt_term
            
            i = pt_met_npts_omgezet["pt"]["ufs"].index(gekozen_pt_term)
            pt_met_npts_omgezet["pt"]["ufs"][i] = pt_term
            
            omgezet.append(pt_met_npts_omgezet)
            
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
