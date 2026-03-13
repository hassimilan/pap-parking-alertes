import requests
import json
import time
import hashlib
import os
import re
import logging
from datetime import datetime
from bs4 import BeautifulSoup

TELEGRAM_BOT_TOKEN = "8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
TELEGRAM_CHAT_ID = "7685475700"
CHECK_INTERVAL = 300
SEEN_FILE = "annonces_vues.json"
PAP_BASE_URL = "https://www.pap.fr/annonce/vente-parking-garage-box-france-g439"
REGLE_1_MOT = "box"
REGLE_1_PRIX_MAX = 15000
REGLE_2_MOTS = ["boxable","boxables","autorisation","accord","possibilité","possibilite","lot","boxer","urgent"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("pap_scraper")

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}

def envoyer_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        log.error("Telegram error: " + str(e))

def extraire_prix(prix_str):
    if not prix_str:
        return None
    chiffres = re.sub(r"[^\d]", "", prix_str)
    try:
        return float(chiffres)
    except:
        return None

def filtrer(annonce):
    texte = (annonce.get("titre","") + " " + annonce.get("description","")).lower()
    raisons = []
    if REGLE_1_MOT in texte:
        prix = extraire_prix(annonce.get("prix",""))
        if prix is None:
            raisons.append("box present (prix non detecte)")
        elif prix < REGLE_1_PRIX_MAX:
            raisons.append("box + prix " + str(int(prix)) + " EUR < 15000 EUR")
    for mot in REGLE_2_MOTS:
        if mot in texte:
            raisons.append("mot cle: " + mot)
            break
    return len(raisons) > 0, raisons

def scraper():
    try:
        r = requests.get(PAP_BASE_URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        log.error("Erreur scraping: " + str(e))
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    cartes = soup.select("a.search-list-item-link, div.search-list-item")
    if not cartes:
        cartes = soup.select("[class*='search-list-item']")
    annonces = []
    for carte in cartes:
        try:
            a = {}
            lien = carte if carte.name == "a" else carte.find("a")
            if lien and lien.get("href"):
                href = lien["href"]
                a["lien"] = href if href.startswith("http") else "https://www.pap.fr" + href
            t = carte.select_one("h2,h3,[class*='title'],[class*='titre']")
            if t:
                a["titre"] = t.get_text(strip=True)
            p = carte.select_one("[class*='price'],[class*='prix']")
            if p:
                a["prix"] = p.get_text(strip=True)
            l = carte.select_one("[class*='location'],[class*='lieu'],[class*='city']")
            if l:
                a["lieu"] = l.get_text(strip=True)
            d = carte.select_one("[class*='desc'],p")
            if d:
                a["description"] = d.get_text(strip=True)
            if a.get("lien") or a.get("titre"):
                annonces.append(a)
        except:
            continue
    log.info(str(len(annonces)) + " annonces trouvees")
    return annonces

def generer_id(a):
    cle = a.get("lien") or a.get("titre","") + a.get("prix","")
    return hashlib.md5(cle.encode()).hexdigest()

def charger():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE,"r") as f:
            return set(json.load(f).get("ids",[]))
    except:
        return set()

def sauvegarder(ids):
    with open(SEEN_FILE,"w") as f:
        json.dump({"ids": list(ids)}, f)

def main():
    log.info("Demarrage PAP Alertes Parking")
    envoyer_telegram("PAP Alertes Parking demarre - surveillance toutes les 5 minutes")
    vues = charger()
    premiere = len(vues) == 0
    while True:
        try:
            annonces = scraper()
            nouvelles = []
            for a in annonces:
                aid = generer_id(a)
                if aid not in vues:
                    vues.add(aid)
                    if not premiere:
                        ok, raisons = filtrer(a)
                        if ok:
                            nouvelles.append((a, raisons))
            if premiere:
                log.info("Premiere execution: " + str(len(annonces)) + " annonces indexees")
                premiere = False
            for a, raisons in nouvelles:
                msg = "NOUVELLE ANNONCE PAP\n" + a.get("titre","") + "\n" + a.get("lieu","") + "\n" + a.get("prix","") + "\n" + " | ".join(raisons) + "\n" + a.get("lien","")
                envoyer_telegram(msg)
                time.sleep(1)
            sauvegarder(vues)
            log.info(str(len(nouvelles)) + " nouvelle(s) annonce(s) matching")
        except Exception as e:
            log.error("Erreur: " + str(e))
        time.sleep(CHECK_INTERVAL)

main()
