import requests,json,time,hashlib,os,re,logging
from bs4 import BeautifulSoup

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300
SEEN="surfaces_vues.json"
PRIX_MAX=60000
PAGES=3

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("surfaces")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

def telegram(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage",json={"chat_id":CHAT,"text":msg},timeout=10)
    except Exception as e:
        log.error(str(e))

def prix_num(s):
    if not s:
        return None
    s=s.replace(".","").replace(" ","").replace("\u202f","").replace("\xa0","")
    c=re.sub(r"[^\d]","",s)
    try:
        v=float(c)
        return v if v>100 else None
    except:
        return None

def scraper():
    res=[]
    for page in range(1,PAGES+1):
        url="https://www.pap.fr/annonce/vente-surface-a-amenager-ile-de-france-g471"
        if page>1:
            url+="?page="+str(page)
        try:
            r=requests.get(url,headers=H,timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.error("Page "+str(page)+": "+str(e))
            continue
        soup=BeautifulSoup(r.text,"html.parser")
        cartes=soup.select("a.search-list-item-link,div.search-list-item")
        if not cartes:
            cartes=soup.select("[class*='search-list-item']")
        if not cartes:
            cartes=soup.select("article")
        log.info("Page "+str(page)+": "+str(len(cartes))+" cartes trouvees")
        for c in cartes:
            try:
                a={}
                l=c if c.name=="a" else c.find("a")
                if l and l.get("href"):
                    h=l["href"]
                    a["lien"]=h if h.startswith("http") else "https://www.pap.fr"+h
                t=c.select_one("h2,h3,[class*='title'],[class*='titre']")
                if t:
                    a["titre"]=t.get_text(strip=True)
                p=c.select_one("[class*='price'],[class*='prix']")
                if p:
                    a["prix"]=p.get_text(strip=True)
                l2=c.select_one("[class*='location'],[class*='lieu'],[class*='city']")
                if l2:
                    a["lieu"]=l2.get_text(strip=True)
                d=c.select_one("[class*='desc'],p")
                if d:
                    a["description"]=d.get_text(strip=True)
                if a.get("lien") or a.get("titre"):
                    res.append(a)
            except:
                continue
        time.sleep(2)
    log.info("Total: "+str(len(res))+" annonces")
    return res

def gen_id(a):
    lien=a.get("lien","")
    m=re.search(r'r(\d+)$',lien)
    if m:
        return m.group(1)
    return hashlib.md5((lien or a.get("titre","")+a.get("prix","")).encode()).hexdigest()

def charger():
    if not os.path.exists(SEEN):
        return set()
    try:
        with open(SEEN,"r") as f:
            return set(json.load(f).get("ids",[]))
    except:
        return set()

def sauver(ids):
    with open(SEEN,"w") as f:
        json.dump({"ids":list(ids)},f)

def main():
    log.info("Demarrage Surfaces IDF")
    telegram("Surfaces IDF demarre - 3 pages - max "+str(PRIX_MAX)+" EUR - toutes les 5 min")
    vues=charger()
    premiere=False
    while True:
        try:
            nouvelles=[]
            for a in scraper():
                aid=gen_id(a)
                if aid not in vues:
                    vues.add(aid)
                    if not premiere:
                        px=prix_num(a.get("prix",""))
                        if px is None or px<=PRIX_MAX:
                            nouvelles.append(a)
            if premiere:
                log.info("Premiere execution - "+str(len(vues))+" annonces indexees")
                premiere=False
            for a in nouvelles:
                px=prix_num(a.get("prix",""))
                msg=("NOUVELLE ANNONCE PAP - SURFACE IDF\n"
                    +a.get("titre","")+"\n"
                    +a.get("lieu","")+"\n"
                    +a.get("prix","")+"\n"
                    +(str(int(px))+" EUR" if px else "prix non renseigne")+"\n"
                    +a.get("lien",""))
                telegram(msg)
                time.sleep(1)
            sauver(vues)
            log.info(str(len(nouvelles))+" nouvelles annonces")
        except Exception as e:
            log.error(str(e))
        time.sleep(INTERVAL)

main()
