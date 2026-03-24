import time
from datetime import datetime
import urllib.request
import subprocess
from selenium import webdriver
import time
from selenium.webdriver.common.by import By

URL = "https://www.doctolib.fr/search?keyword=medecin-generaliste&location=versailles"

firefoxOptions = webdriver.FirefoxOptions()
firefoxOptions.headless = True
browser = webdriver.Firefox(options=firefoxOptions)
browser.get(URL)
time.sleep(2)
h2s = browser.find_elements(By.TAG_NAME, "h2")
h2s = [h for h in h2s if h.text.startswith("Dr")]
idx = 1
for h2 in h2s:
    browser.execute_script("arguments[0].scrollIntoView();", h2)
    time.sleep(1)
    
    try:
        card = h2.find_element(By.XPATH, "./ancestor::div[contains(@class,'dl-card')]")
        lines = [l.strip() for l in card.text.splitlines() if l.strip()]
        
        nom        = lines[0]                    # Dr Corinne BOYER
        specialite = lines[1]                    # Médecin généraliste
        adresse    = " ".join(lines[2:4])        # 26 BIS Rue Coste 78000 Versailles
        secteur    = lines[4]                    # Conventionné secteur 1
        #dispo      = lines[-1] if "Prochaine disponibilité" in card.text else "Aucune disponibilité"
        texte = card.text
        if "Prochaine disponibilité" in texte:
            dispo = texte.split("Prochaine disponibilité")[-1].strip().replace("\n", " ")
        else:
            dispo = "Aucune disponibilité"
        print(f"{nom} | {specialite}")
        print(f"{adresse} | {secteur}")
        print(f"Dispo: {dispo}")
        print("---")
        if idx >= 5:
            break
        idx += 1

    except Exception as e:
        print(f"Erreur: {e}")
#browser.close()
