import requests
import json
import time
import hashlib
import os
import re
import logging
from bs4 import BeautifulSoup

TELEGRAM_BOT_TOKEN = "8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
TELEGRAM_CHAT_ID = "7685475700"
CHECK_INTERVAL = 300
SEEN_FILE = "annonces_vues.json"

REGLE_2_MOTS = ["boxable","boxables","autorisation","accord","possibilite","possibilité","lot","boxer","urgent","fermer"]

ARRONDISSEMENTS = {
    "75001":(15000,30000),"75002":(15000,30000),"75003":(10000,30000),
    "75004":(15000,30000),"75005":(10000,25000),"75006":(15000,30000),
    "75007":(15000,30000),"75008":(15000,30000),"75009":(10000,20000),
    "75010":(4000,11000),"75011":(5000,13000),"75012":(4000,13000),
    "75013":(4000,8000),"75014":(4000,11000),"75015":(3000,12000),
    "75016":(5000,25000),"75017":(5000,25000),"75018":(2000,10000),
    "75019":(2000,10000),"75020":(0,10000)
}

URLS = {
    "france":"https://www.pap.fr/annonce/vente-parking-garage-box-france-g439",
    "75001":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-1er-g439g196",
    "75002":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-2e-g439g197",
    "75003":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-3e-g439g198",
    "75004":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-4e-g439g199",
    "75005":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-5e-g439g200",
    "75006":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-6e-g439g201",
    "75007":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-7e-g439g202",
    "75008":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-8e-g439g203",
    "75009":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-9e-g439g204",
    "75010":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-10e-g439g205",
    "75011":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-11e-g439g206",
    "75012":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-12e-g439g207",
    "75013":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-13e-g439g208",
    "75014":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-14e-g439g209",
    "75015":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-15e-g439g210",
    "75016":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-16e-g439g211",
    "75017":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-17e-g439g212",
    "75018":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-18e-g439g213",
    "75019":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-19e-g439g214",
    "75020":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-20e-g439g215",
"paris-surfaces":"https://www.pap.fr/annonce/vente-surface-a-amenager-ile-de-france-g471"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("pap")

HEADERS = {"User-Agent":"Mozilla/5.0 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9"}

def envoyer_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    try:
        requests.post(url, json={"chat_id":TELEGRAM_CHAT_ID,"text":message}, timeout=10)
    except Exception as e:
        log.error("Telegram: " + str(e))

def extraire_prix(s):
    if not s:
        return None
    s = s.replace(".","")\
         .replace(" ","")\
         .replace("\u202f","")\
         .replace("\xa0","")
    chiffres = re.sub(r"[^\d]","",s)
    try:
        v = float(chiffres)
        return v if v > 100 else None
    except:
        return None

def detecter_arrondissement_depuis_lien(lien):
    if not lien:
        return None
    for code in ARRONDISSEMENTS:
        if code in lien:
            return code
    return None

def filtrer(annonce, zone):
    texte = (annonce.get("titre","") + " " + annonce.get("description","")).lower()
    lien = annonce.get("lien","")
    prix = extraire_prix(annonce.get("prix",""))
    raisons = []

    if zone == "paris-surfaces":
        if prix is not None and prix > 60000:
            return False, []
        if prix:
            raisons.append("Surface a amenager IDF - " + str(int(prix)) + " EUR")
        else:
            raisons.append("Surface a amenager IDF")
        return True, raisons
        return False, []
    raisons.append("Surface a amenager IDF - " + str(int(prix)) + " EUR" if prix else "Surface a amenager IDF")
    return True, raisons

    if zone in ARRONDISSEMENTS:
        arr_reel = detecter_arrondissement_depuis_lien(lien) or zone
        if arr_reel != zone:
            return False, []
        prix_min, prix_max = ARRONDISSEMENTS[zone]
        if prix is not None and prix_min <= prix <= prix_max:
            raisons.append("Paris " + zone + " - " + str(int(prix)) + " EUR (fourchette " + str(prix_min) + "-" + str(prix_max) + " EUR)")
        else:
            for mot in REGLE_2_MOTS:
                if mot in texte:
                    raisons.append("mot cle: " + mot)
                    break
            return len(raisons) > 0, raisons

    if zone == "france":
        if "box" in texte:
            if prix is None:
                raisons.append("box present (prix non detecte)")
            elif prix < 15000:
                raisons.append("box + " + str(int(prix)) + " EUR < 15000 EUR")

    for mot in REGLE_2_MOTS:
        if mot in texte:
            raisons.append("mot cle: " + mot)
            break

    return len(raisons) > 0, raisons

def scraper(url, zone):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        log.error("Scraping " + zone + ": " + str(e))
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
    log.info(zone + ": " + str(len(annonces)) + " annonces")
    return annonces

def generer_id(a, zone):
    cle = zone + (a.get("lien") or a.get("titre","") + a.get("prix",""))
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
        json.dump({"ids":list(ids)}, f)

def main():
    log.info("Demarrage")
    envoyer_telegram("PAP Alertes Parking demarre - Paris + France toutes les 5 min")
    vues = charger()
    premiere = len(vues) == 0
    while True:
        try:
            nouvelles = []
            for zone, url in URLS.items():
                annonces = scraper(url, zone)
                for a in annonces:
                    aid = generer_id(a, zone)
                    if aid not in vues:
                        vues.add(aid)
                        if not premiere:
                            ok, raisons = filtrer(a, zone)
                            if ok:
                                nouvelles.append((a, raisons, zone))
                time.sleep(2)
            if premiere:
                log.info("Premiere execution - " + str(len(vues)) + " annonces indexees")
                premiere = False
            for a, raisons, zone in nouvelles:
                msg = ("NOUVELLE ANNONCE PAP\n"
                    + a.get("titre","") + "\n"
                    + a.get("lieu","") + "\n"
                    + a.get("prix","") + "\n"
                    + " | ".join(raisons) + "\n"
                    + a.get("lien",""))
                envoyer_telegram(msg)
                time.sleep(1)
            sauvegarder(vues)
            log.info(str(len(nouvelles)) + " matching")
        except Exception as e:
            log.error("Erreur: " + str(e))
        time.sleep(CHECK_INTERVAL)

main()
