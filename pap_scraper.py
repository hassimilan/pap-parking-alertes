import requests,json,time,hashlib,os,re,logging
from bs4 import BeautifulSoup
if os.path.exists("annonces_vues.json"): os.remove("annonces_vues.json")

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300
SEEN="annonces_vues.json"
URLS_PAGES=["https://www.pap.fr/annonce/vente-parking-garage-box-france-g439","https://www.pap.fr/annonce/vente-parking-garage-box-france-g439?page=2","https://www.pap.fr/annonce/vente-parking-garage-box-france-g439?page=3"]
MOTS=["boxable","boxables","autorisation","accord","possibilite","possibilité","lot","boxer","urgent","fermer"]
ARR={"75001":(15000,30000),"75002":(15000,30000),"75003":(10000,30000),"75004":(15000,30000),"75005":(10000,25000),"75006":(15000,30000),"75007":(15000,30000),"75008":(15000,30000),"75009":(10000,20000),"75010":(4000,11000),"75011":(5000,13000),"75012":(4000,13000),"75013":(4000,8000),"75014":(4000,11000),"75015":(3000,12000),"75016":(5000,25000),"75017":(5000,25000),"75018":(2000,10000),"75019":(2000,10000),"75020":(0,10000)}

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("pap")
H={"User-Agent":"Mozilla/5.0 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"fr-FR,fr;q=0.9"}

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

def arr_depuis_lien(lien):
    if not lien:
        return None
    m=re.search(r'paris-\d+e[r]?-(\d{5})',lien)
    if m:
        code=m.group(1)
        if code in ARR:
            return code
    return None

def scraper():
    res=[]
    for url in URLS_PAGES:
        try:
            r=requests.get(url,headers=H,timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.error("Scraping: "+str(e))
            continue
        soup=BeautifulSoup(r.text,"html.parser")
        cartes=soup.select("a.search-list-item-link,div.search-list-item") or soup.select("[class*='search-list-item']")
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
    log.info(str(len(res))+" annonces trouvees")
    return res
    
def gen_id(a):
    lien=a.get("lien","")
    m=re.search(r'r(\d+)$',lien)
    if m:
        return m.group(1)
    return hashlib.md5((lien or a.get("titre","")+a.get("prix","")).encode()).hexdigest()

def filtrer(a):
    texte=(a.get("titre","")+a.get("description","")).lower()
    lien=a.get("lien","")
    px=prix_num(a.get("prix",""))
    raisons=[]
    arr=arr_depuis_lien(lien)
    if arr:
        pmin,pmax=ARR[arr]
        if px is not None and pmin<=px<=pmax:
            raisons.append("Paris "+arr+" - "+str(int(px))+" EUR ("+str(pmin)+"-"+str(pmax)+" EUR)")
        else:
            for m in MOTS:
                if m in texte:
                    raisons.append("mot cle: "+m)
                    break
            return len(raisons)>0,raisons
    else:
        if "box" in texte:
            if px is None:
                raisons.append("box present (prix non detecte)")
            elif px<15000:
                raisons.append("box + "+str(int(px))+" EUR < 15000 EUR")
    for m in MOTS:
        if m in texte:
            raisons.append("mot cle: "+m)
            break
    return len(raisons)>0,raisons

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
    log.info("Demarrage PAP Parking")
    telegram("PAP Alertes Parking demarre - France entiere toutes les 5 min")
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
                        ok,raisons=filtrer(a)
                        if ok:
                            nouvelles.append((a,raisons))
            if premiere:
                log.info("Premiere execution - "+str(len(vues))+" annonces indexees")
                premiere=False
            for a,raisons in nouvelles:
                msg=("NOUVELLE ANNONCE PAP PARKING\n"
                    +a.get("titre","")+"\n"
                    +a.get("lieu","")+"\n"
                    +a.get("prix","")+"\n"
                    +" | ".join(raisons)+"\n"
                    +a.get("lien",""))
                telegram(msg)
                time.sleep(1)
            sauver(vues)
            log.info(str(len(nouvelles))+" matching")
        except Exception as e:
            log.error(str(e))
        time.sleep(INTERVAL)

main()
