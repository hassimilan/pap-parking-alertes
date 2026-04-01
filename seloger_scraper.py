import requests,json,time,hashlib,os,re,logging
from bs4 import BeautifulSoup

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300
SEEN="seloger_vues.json"

MOTS=["boxable","boxables","autorisation","accord","boxer","urgent","fermer","renover","rénover","ag","construire","cloture","clôturer","cloturer"]

PAGES=[
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=750000&furnished=0",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=750000&furnished=0&LISTING-LISTpg=2",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=750000&furnished=0&LISTING-LISTpg=3",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=590000&furnished=0",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=590000&furnished=0&LISTING-LISTpg=2",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=670000&furnished=0",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&qsVersion=1.0&m=search_results&ci=670000&furnished=0&LISTING-LISTpg=2",
]

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("seloger")

H={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language":"fr-FR,fr;q=0.9",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer":"https://www.seloger.com/"
}

def telegram(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage",json={"chat_id":CHAT,"text":msg},timeout=10)
    except Exception as e:
        log.error(str(e))

def scraper():
    res=[]
    ids_vus=set()
    for url in PAGES:
        try:
            r=requests.get(url,headers=H,timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.error("Erreur: "+str(e))
            time.sleep(5)
            continue
        soup=BeautifulSoup(r.text,"html.parser")
        cartes=soup.select("[class*='CardsList']") or soup.select("[class*='listing']") or soup.select("article")
        log.info(str(len(cartes))+" cartes trouvees sur "+url[-30:])
        for c in cartes:
            try:
                a={}
                l=c.find("a")
                if l and l.get("href"):
                    h=l["href"]
                    a["lien"]=h if h.startswith("http") else "https://www.seloger.com"+h
                t=c.select_one("h2,h3,[class*='title'],[class*='Title']")
                if t:
                    a["titre"]=t.get_text(strip=True)
                p=c.select_one("[class*='price'],[class*='Price'],[class*='prix']")
                if p:
                    a["prix"]=p.get_text(strip=True)
                l2=c.select_one("[class*='location'],[class*='Location'],[class*='city']")
                if l2:
                    a["lieu"]=l2.get_text(strip=True)
                d=c.select_one("[class*='desc'],[class*='Desc'],[class*='summary'],[class*='Summary']")
                if d:
                    a["description"]=d.get_text(strip=True)
                if a.get("lien") or a.get("titre"):
                    uid=re.search(r'(\d{6,})',a.get("lien",""))
                    uid=uid.group(1) if uid else a.get("lien","")
                    if uid not in ids_vus:
                        ids_vus.add(uid)
                        res.append(a)
            except:
                continue
        time.sleep(3)
    log.info("Total: "+str(len(res))+" annonces")
    return res

def gen_id(a):
    lien=a.get("lien","")
    m=re.search(r'(\d{6,})',lien)
    if m:
        return m.group(1)
    return hashlib.md5((lien or a.get("titre","")+a.get("prix","")).encode()).hexdigest()

def filtrer(a):
    texte=(str(a.get("titre",""))+str(a.get("description",""))).lower()
    for m in MOTS:
        if m in texte:
            return True,"mot cle: "+m
    return False,""

def charger():
    if os.path.exists(SEEN):
        os.remove(SEEN)
    return set()

def sauver(ids):
    with open(SEEN,"w") as f:
        json.dump({"ids":list(ids)},f)

def main():
    log.info("Demarrage SeLoger")
    telegram("SeLoger Alertes Parking demarre - IDF + Hauts de France + Grand Est - toutes les 5 min")
    vues=charger()
    premiere=len(vues)==0
    while True:
        try:
            nouvelles=[]
            for a in scraper():
                aid=gen_id(a)
                if aid not in vues:
                    vues.add(aid)
                    if not premiere:
                        ok,raison=filtrer(a)
                        if ok:
                            nouvelles.append((a,raison))
            if premiere:
                log.info("Premiere execution - "+str(len(vues))+" annonces indexees")
                premiere=False
            for a,raison in nouvelles:
                msg=("NOUVELLE ANNONCE SELOGER\n"
                    +a.get("titre","")+"\n"
                    +a.get("lieu","")+"\n"
                    +a.get("prix","")+"\n"
                    +raison+"\n"
                    +a.get("lien",""))
                telegram(msg)
                time.sleep(1)
            sauver(vues)
            log.info(str(len(nouvelles))+" matching")
        except Exception as e:
            log.error(str(e))
        time.sleep(INTERVAL)

main()
