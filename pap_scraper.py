import requests,json,time,hashlib,os,re,logging
from bs4 import BeautifulSoup
import threading

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300

MOTS=["boxable","boxables","autorisation","accord","boxer","urgent","fermer","renover","rénover","ag ","construire","cloture","clôturer","cloturer"]

PAP_PAGES=[
    "https://www.pap.fr/annonce/vente-parking-garage-box-france-g439",
    "https://www.pap.fr/annonce/vente-parking-garage-box-france-g439?page=2",
]

SELOGER_PAGES=[
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&furnished=0&ci=750000",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&furnished=0&ci=590000",
    "https://www.seloger.com/list.htm?types=4&projects=2&natures=1&enterprise=0&furnished=0&ci=670000",
]

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("scraper")

PAP_H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9"}
SL_H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9","Referer":"https://www.seloger.com/"}

def telegram(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage",json={"chat_id":CHAT,"text":msg},timeout=10)
    except Exception as e:
        log.error(str(e))

def scraper_html(pages,headers,nom):
    res=[]
    ids_vus=set()
    for url in pages:
        try:
            r=requests.get(url,headers=headers,timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.error(nom+": "+str(e))
            time.sleep(5)
            continue
        soup=BeautifulSoup(r.text,"html.parser")
        cartes=soup.select("a.search-list-item-link,div.search-list-item,[class*='search-list-item'],article")
        log.info(nom+": "+str(len(cartes))+" cartes")
        for c in cartes:
            try:
                a={}
                l=c if c.name=="a" else c.find("a")
                if l and l.get("href"):
                    h=l["href"]
                    a["lien"]=h if h.startswith("http") else "https://www."+nom.lower()+".fr"+h
                t=c.select_one("h2,h3,[class*='title'],[class*='titre'],[class*='Title']")
                if t:
                    a["titre"]=t.get_text(strip=True)
                p=c.select_one("[class*='price'],[class*='prix'],[class*='Price']")
                if p:
                    a["prix"]=p.get_text(strip=True)
                l2=c.select_one("[class*='location'],[class*='lieu'],[class*='city'],[class*='Location']")
                if l2:
                    a["lieu"]=l2.get_text(strip=True)
                d=c.select_one("[class*='desc'],[class*='Desc'],[class*='summary'],p")
                if d:
                    a["description"]=d.get_text(strip=True)
                a["source"]=nom
                if a.get("lien") or a.get("titre"):
                    uid=re.search(r'(\d{6,})',a.get("lien",""))
                    uid=nom+(uid.group(1) if uid else a.get("lien",""))
                    if uid not in ids_vus:
                        ids_vus.add(uid)
                        res.append(a)
            except:
                continue
        time.sleep(3)
    return res
def gen_id(a):
    lien=a.get("lien","")
    source=a.get("source","")
    m=re.search(r'(\d{6,})',lien)
    if m:
        return source+m.group(1)
    return hashlib.md5((source+lien or a.get("titre","")+a.get("prix","")).encode()).hexdigest()

def filtrer(a):
    texte=(str(a.get("titre",""))+str(a.get("description",""))).lower()
    for m in MOTS:
        if m in texte:
            return True,"mot cle: "+m.strip()
    return False,""

def charger(f):
    if os.path.exists(f):
        os.remove(f)
    return set()

def sauver(ids,f):
    with open(f,"w") as fp:
        json.dump({"ids":list(ids)},fp)

def run_scraper(pages,headers,nom,seen_file):
    log.info("Demarrage "+nom)
    telegram(nom+" demarre - mots cles - toutes les 5 min")
    vues=charger(seen_file)
    premiere=len(vues)==0
    while True:
        try:
            nouvelles=[]
            for a in scraper_html(pages,headers,nom):
                aid=gen_id(a)
                if aid not in vues:
                    vues.add(aid)
                    if not premiere:
                        ok,raison=filtrer(a)
                        if ok:
                            nouvelles.append((a,raison))
            if premiere:
                log.info(nom+" premiere execution - "+str(len(vues))+" annonces")
                premiere=False
            for a,raison in nouvelles:
                msg=("NOUVELLE ANNONCE "+nom+"\n"
                    +a.get("titre","")+"\n"
                    +a.get("lieu","")+"\n"
                    +a.get("prix","")+"\n"
                    +raison+"\n"
                    +a.get("lien",""))
                telegram(msg)
                time.sleep(1)
            sauver(vues,seen_file)
            log.info(nom+" "+str(len(nouvelles))+" matching")
        except Exception as e:
            log.error(nom+" erreur: "+str(e))
        time.sleep(INTERVAL)

if __name__=="__main__":
    t1=threading.Thread(target=run_scraper,args=(PAP_PAGES,PAP_H,"PAP","pap_vues.json"),daemon=True)
    t2=threading.Thread(target=run_scraper,args=(SELOGER_PAGES,SL_H,"SeLoger","seloger_vues.json"),daemon=True)
    t1.start()
    t2.start()
    log.info("Les deux scrapers tournent")
    t1.join()
    t2.join()
