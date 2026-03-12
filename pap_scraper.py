#!/usr/bin/env python3
"""
PAP Alertes Parking — Scraper avec notifications Telegram
Surveille les nouvelles annonces de parkings à vendre sur PAP.fr
et envoie une alerte Telegram dès qu'une nouvelle annonce apparaît.
"""

import requests
import json
import time
import hashlib
import os
import logging
from datetime import datetime
from bs4 import BeautifulSoup

TELEGRAM_BOT_TOKEN = "8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
TELEGRAM_CHAT_ID   = "7685475700"

CHECK_INTERVAL = 300
SEEN_FILE = "annonces_vues.json"

CRITERES = {
    "prix_max": None,
    "prix_min": None,
    "ville":    None,
}

REGLE_1_MOT      = "box"
REGLE_1_PRIX_MAX = 15000

REGLE_2_MOTS = [
    "boxable", "boxables", "autorisation",
    "accord", "possibilité", "possibilite", "lot", "boxer",
]

PAP_BASE_URL = "https://www.pap.fr/annonce/vente-parking-garage-box-france-g439"

def construire_url():
    url = PAP_BASE_URL
    params = []
    if CRITERES.get("prix_max"):
        params.append(f"prix-max={CRITERES['prix_max']}")
    if CRITERES.get("prix_min"):
        params.append(f"prix-min={CRITERES['prix_min']}")
    if params:
        url += "?" + "&".join(params)
    return url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pap_scraper.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(_name_)

def envoyer_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Erreur Telegram : {e}")
        return False

def extraire_prix_numerique(prix_str: str):
    if not prix_str:
        return None
    import re
    chiffres = re.sub(r"[^\d,.]", "", prix_str).replace(",", ".")
    try:
        return float(chiffres)
    except ValueError:
        return None

def annonce_correspond_aux_filtres(annonce: dict):
    texte = " ".join([
        annonce.get("titre", ""),
        annonce.get("description", ""),
        annonce.get("lieu", ""),
    ]).lower()
    raisons = []
    if REGLE_1_MOT in texte.split() or f" {REGLE_1_MOT} " in f" {texte} ":
        prix_num = extraire_prix_numerique(annonce.get("prix", ""))
        if prix_num is not None and prix_num < REGLE_1_PRIX_MAX:
            raisons.append(f"Regle 1 : contient box + prix {int(prix_num)} EUR < {REGLE_1_PRIX_MAX} EUR")
        elif prix_num is None:
            raisons.append("Regle 1 : contient box (prix non detecte, a verifier)")
    for mot in REGLE_2_MOTS:
        if mot in texte:
            raisons.append(f"Regle 2 : contient le mot cle {mot}")
            break
    return (len(raisons) > 0, raisons)

def notifier_nouvelle_annonce(annonce: dict, raisons: list):
    prix = annonce.get("prix", "Prix non renseigne")
    titre = annonce.get("titre", "Parking / Garage / Box")
    lieu = annonce.get("lieu", "France")
    lien = annonce.get("lien", "")
    description = annonce.get("description", "")
    date = annonce.get("date", "")
    message = (
        f"Nouvelle annonce PAP - Parking a vendre\n\n"
        f"{titre}\n{lieu}\n{prix}\n"
    )
    if date:
        message += f"{date}\n"
    message += f"\n{' | '.join(raisons)}\n"
    if description:
        message += f"\n{description[:200]}\n"
    if lien:
        message += f"\n{lien}"
    envoyer_telegram(message)

def charger_annonces_vues() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    except Exception:
        return set()

def sauvegarder_annonces_vues(ids: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": list(ids), "derniere_maj": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

def generer_id(annonce: dict) -> str:
    cle = annonce.get("lien") or annonce.get("titre", "") + annonce.get("prix", "")
    return hashlib.md5(cle.encode()).hexdigest()
  HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

def scraper_pap() -> list:
    url = construire_url()
    log.info(f"Scraping : {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Erreur scraping PAP : {e}")
        return []
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    annonces = []
    cartes = soup.select("a.search-list-item-link, div.search-list-item")
    if not cartes:
        cartes = soup.select("[class*='search-list-item']")
    log.info(f"{len(cartes)} annonce(s) trouvee(s)")
    for carte in cartes:
        try:
            annonce = extraire_annonce(carte)
            if annonce:
                annonces.append(annonce)
        except Exception as e:
            log.debug(f"Erreur extraction : {e}")
    return annonces

def extraire_annonce(element):
    annonce = {}
    lien_el = element if element.name == "a" else element.find("a")
    if lien_el and lien_el.get("href"):
        href = lien_el["href"]
        annonce["lien"] = href if href.startswith("http") else f"https://www.pap.fr{href}"
    titre_el = element.select_one("h2, h3, [class*='title'], [class*='titre']")
    if titre_el:
        annonce["titre"] = titre_el.get_text(strip=True)
    prix_el = element.select_one("[class*='price'], [class*='prix']")
    if prix_el:
        annonce["prix"] = prix_el.get_text(strip=True)
    lieu_el = element.select_one("[class*='location'], [class*='lieu'], [class*='city']")
    if lieu_el:
        annonce["lieu"] = lieu_el.get_text(strip=True)
    desc_el = element.select_one("[class*='description'], [class*='desc'], p")
    if desc_el:
        annonce["description"] = desc_el.get_text(strip=True)
    date_el = element.select_one("[class*='date'], time")
    if date_el:
        annonce["date"] = date_el.get_text(strip=True)
    if not annonce.get("lien") and not annonce.get("titre"):
        return None
    return annonce

def main():
    log.info("PAP Alertes Parking - Demarrage")
    if TELEGRAM_BOT_TOKEN == "VOTRE_BOT_TOKEN":
        log.error("Configurez votre TELEGRAM_BOT_TOKEN dans le script !")
        return
    envoyer_telegram(
        f"PAP Alertes Parking demarre\n"
        f"Surveillance des parkings a vendre sur PAP.fr\n"
        f"Verification toutes les {CHECK_INTERVAL // 60} minutes"
    )
    annonces_vues = charger_annonces_vues()
    premiere_execution = len(annonces_vues) == 0
    log.info(f"{len(annonces_vues)} annonce(s) deja connue(s)")
    while True:
        try:
            annonces = scraper_pap()
            nouvelles = []
            for annonce in annonces:
                aid = generer_id(annonce)
                if aid not in annonces_vues:
                    annonces_vues.add(aid)
                    if not premiere_execution:
                        correspond, raisons = annonce_correspond_aux_filtres(annonce)
                        if correspond:
                            nouvelles.append((annonce, raisons))
                        else:
                            log.info(f"Ignoree : {annonce.get('titre', '')[:60]}")
            if premiere_execution:
                log.info(f"Premiere execution : {len(annonces)} annonce(s) indexee(s).")
                premiere_execution = False
            elif nouvelles:
                log.info(f"{len(nouvelles)} nouvelle(s) annonce(s) trouvee(s) !")
                for annonce, raisons in nouvelles:
                    notifier_nouvelle_annonce(annonce, raisons)
                    time.sleep(1)
            else:
                log.info("Aucune nouvelle annonce.")
            sauvegarder_annonces_vues(annonces_vues)
        except KeyboardInterrupt:
            log.info("Arret du script")
            envoyer_telegram("PAP Alertes Parking arrete.")
            break
        except Exception as e:
            log.error(f"Erreur : {e}")
        log.info(f"Prochaine verification dans {CHECK_INTERVAL // 60} min...")
        time.sleep(CHECK_INTERVAL)

if _name_ == "_main_":
    main()
