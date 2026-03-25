import re
import time

from mcp import types
from selenium import webdriver
from selenium.webdriver.common.by import By


# =================================================================
# DOCTOLIB
# =================================================================
async def call_doctolib_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "doctolib_search":
        raise ValueError(f"Unknown tool: {name}")

    params = {"spec": arguments["spec"], "location": arguments.get("location", ""), "limit": arguments.get("limit", 5)}
    print(f"Recherche Doctolib avec params: {params}")

    spec = params["spec"].replace(" ", "-").lower()
    base_url = "https://www.doctolib.fr/search"
    URL = f"{base_url}?keyword={spec}&location={'location' in params and params['location'].replace(' ', '+').lower() or ''}"
    print(f"URL de recherche Doctolib: {URL}")

    firefoxOptions = webdriver.FirefoxOptions()
    firefoxOptions.headless = True
    browser = webdriver.Firefox(options=firefoxOptions)
    browser.get(URL)
    time.sleep(3)

    h2s = browser.find_elements(By.TAG_NAME, "h2")
    h2s = [h for h in h2s if h.text.strip().startswith("Dr") or h.text.strip().startswith("M.") or h.text.strip().startswith("Mme")]

    list_results = ""

    for h2 in h2s:
        browser.execute_script("arguments[0].scrollIntoView();", h2)
        time.sleep(2)
        try:
            card = h2.find_element(By.XPATH, "./ancestor::div[contains(@class,'dl-card')]")
            if "Ce soignant réserve la prise de rendez-vous en ligne aux patients déjà suivis" in card.text:
                continue
            text = " ".join(card.text.splitlines())
            match_date_heure = re.search(
                r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+\d{1,2}\s+\w+(?:\s+\d{4})?\s+(\d{2}:\d{2})", text, re.IGNORECASE
            )
            match_prochain = re.search(r"Prochain RDV le \d{1,2} \w+ \d{4}", text)

            if match_date_heure:
                dispo = match_date_heure.group().strip()
            elif match_prochain:
                dispo = match_prochain.group().strip()
            else:
                continue

            lines = [l.strip() for l in card.text.splitlines() if l.strip()]
            nom = lines[0]
            specialite = lines[1]
            adresse = " ".join(lines[2:4])
            secteur = lines[4]

            list_results += f"{nom} | {specialite}\n"
            list_results += f"{adresse} | {secteur}\n"
            list_results += f"Dispo: {dispo}\n"
            list_results += "---\n"
            print(f"{nom} | {dispo}")
        except Exception as e:
            print(f"Erreur: {e}")

    browser.close()
    return [types.TextContent(type="text", text=list_results)]
