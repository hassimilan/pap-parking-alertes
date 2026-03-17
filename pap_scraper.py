import requests,json,time,hashlib,os,re,logging
from bs4 import BeautifulSoup

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300
SEEN="annonces_vues.json"
MOTS=["boxable","boxables","autorisation","accord","possibilite","possibilité","lot","boxer","urgent","fermer"]
ARR={"75001":(15000,30000),"75002":(15000,30000),"75003":(10000,30000),"75004":(15000,30000),"75005":(10000,25000),"75006":(15000,30000),"75007":(15000,30000),"75008":(15000,30000),"75009":(10000,20000),"75010":(4000,11000),"75011":(5000,13000),"75012":(4000,13000),"75013":(4000,8000),"75014":(4000,11000),"75015":(3000,12000),"75016":(5000,25000),"75017":(5000,25000),"75018":(2000,10000),"75019":(2000,10000),"75020":(0,10000)}
URLS={"75001":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-1er-g439g196","75002":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-2e-g439g197","75003":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-3e-g439g198","75004":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-4e-g439g199","75005":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-5e-g439g200","75006":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-6e-g439g201","75007":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-7e-g439g202","75008":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-8e-g439g203","75009":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-9e-g439g204","75010":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-10e-g439g205","75011":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-11e-g439g206","75012":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-12e-g439g207","75013":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-13e-g439g208","75014":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-14e-g439g209","75015":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-15e-g439g210","75016":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-16e-g439g211","75017":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-17e-g439g212","75018":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-18e-g439g213","75019":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-19e-g439g214","75020":"https://www.pap.fr/annonce/vente-parking-garage-box-paris-20e-g439g215","france":"https://www.pap.fr/annonce/vente-parking-garage-box-france-g439","surfaces":"https://www.pap.fr/annonce/vente-surface-a-amenager-ile-de-france-g471"}

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
    for code in ARR:
        if code in lien:
            return code
    return None

def scraper(url,zone):
    try:
        r=requests.get(url,headers=H,timeout=20)
        r.raise_for_status()
    except Exception as e:
        log.error(zone+": "+str(e))
        return []
    soup=BeautifulSoup(r.text,"html.parser")
    cartes=soup.select("a.search-list-item-link,div.search-list-item") or soup.select("[class*='search-list-item']")
    res=[]
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
    log.info(zone+": "+str(len(res)))
    return res
def filtrer(a,zone):
    texte=(a.get("titre","")+a.get("description","")).lower()
    lien=a.get("lien","")
    px=prix_num(a.get("prix",""))
    raisons=[]

    if zone in ARR:
        arr_reel=arr_depuis_lien(lien)
        if arr_reel and arr_reel!=zone:
            return False,[]
        pmin,pmax=ARR[zone]
        if px is not None and pmin<=px<=pmax:
            raisons.append("Paris "+zone+" - "+str(int(px))+" EUR ("+str(pmin)+"-"+str(pmax)+" EUR)")
        else:
            for m in MOTS:
                if m in texte:
                    raisons.append("mot cle: "+m)
                    break
            return len(raisons)>0,raisons

    elif zone=="france":
        arr_reel=arr_depuis_lien(lien)
        if arr_reel:
            return False,[]
        if "box" in texte:
            if px is None:
                raisons.append("box present (prix non detecte)")
            elif px<15000:
                raisons.append("box + "+str(int(px))+" EUR < 15000 EUR")

    elif zone=="surfaces":
        arr_reel=arr_depuis_lien(lien)
        if arr_reel:
            return False,[]
        if px is not None and px>60000:
            return False,[]
        raisons.append("Surface a amenager IDF"+((" - "+str(int(px))+" EUR") if px else ""))

    for m in MOTS:
        if m in texte:
            raisons.append("mot cle: "+m)
            break

    return len(raisons)>0,raisons

def gen_id(a,zone):
    return hashlib.md5((zone+(a.get("lien") or a.get("titre","")+a.get("prix",""))).encode()).hexdigest()

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
    log.info("Demarrage")
    telegram("PAP Alertes Parking demarre - Paris + France + Surfaces toutes les 5 min")
    vues=charger()
    premiere=len(vues)==0
    while True:
        try:
            nouvelles=[]
            for zone,url in URLS.items():
                for a in scraper(url,zone):
                    aid=gen_id(a,zone)
                    if aid not in vues:
                        vues.add(aid)
                        if not premiere:
                            ok,raisons=filtrer(a,zone)
                            if ok:
                                nouvelles.append((a,raisons))
                time.sleep(2)
            if premiere:
                log.info("Premiere execution - "+str(len(vues))+" annonces")
                premiere=False
            for a,raisons in nouvelles:
                msg="NOUVELLE ANNONCE PAP\n"+a.get("titre","")+"\n"+a.get("lieu","")+"\n"+a.get("prix","")+"\n"+" | ".join(raisons)+"\n"+a.get("lien","")
                telegram(msg)
                time.sleep(1)
            sauver(vues)
            log.info(str(len(nouvelles))+" matching")
        except Exception as e:
            log.error(str(e))
        time.sleep(INTERVAL)

main()
