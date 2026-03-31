import requests,json,time,hashlib,os,re,logging

TOKEN="8619174227:AAGfg_JRsA6D9yvDT9On2lrapjrSiaLXmRU"
CHAT="7685475700"
INTERVAL=300
SEEN="annonces_vues.json"
MOTS=["boxable","boxables","autorisation","accord","possibilite","possibilité","lot","boxer","urgent","fermer"]
ARR={"75001":(15000,30000),"75002":(15000,30000),"75003":(10000,30000),"75004":(15000,30000),"75005":(10000,25000),"75006":(15000,30000),"75007":(15000,30000),"75008":(15000,30000),"75009":(10000,20000),"75010":(4000,11000),"75011":(5000,13000),"75012":(4000,13000),"75013":(4000,8000),"75014":(4000,11000),"75015":(3000,12000),"75016":(5000,25000),"75017":(5000,25000),"75018":(2000,10000),"75019":(2000,10000),"75020":(0,10000)}

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("pap")

H={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept":"application/json, text/plain, /",
    "Accept-Language":"fr-FR,fr;q=0.9",
    "Referer":"https://www.pap.fr/",
    "Origin":"https://www.pap.fr"
}

API_URL="https://ws.pap.fr/immobilier/annonces?typeBien[]=parking-garage-box&typeTransaction=vente&geo[]=ile-de-france&nbResultats=100&tri=date-desc"
API_FRANCE="https://ws.pap.fr/immobilier/annonces?typeBien[]=parking-garage-box&typeTransaction=vente&nbResultats=100&tri=date-desc"

def telegram(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage",json={"chat_id":CHAT,"text":msg},timeout=10)
    except Exception as e:
        log.error(str(e))

def prix_num(s):
    if not s:
        return None
    s=str(s).replace(".","").replace(" ","").replace("\u202f","").replace("\xa0","")
    c=re.sub(r"[^\d]","",s)
    try:
        v=float(c)
        return v if v>100 else None
    except:
        return None

def arr_depuis_texte(texte,lien):
    if lien:
        m=re.search(r'paris-\d+e[r]?-(750\d\d)',lien)
        if m and m.group(1) in ARR:
            return m.group(1)
    for code in ARR:
        if code in str(texte):
            return code
    return None

def scraper():
    res=[]
    for url in [API_FRANCE]:
        try:
            r=requests.get(url,headers=H,timeout=20)
            r.raise_for_status()
            data=r.json()
            annonces=data.get("annonces",data.get("items",data.get("results",[])))
            if isinstance(annonces,list):
                for a in annonces:
                    try:
                        lien=a.get("urlAnnonce",a.get("url",""))
                        if lien and not lien.startswith("http"):
                            lien="https://www.pap.fr"+lien
                        prix=a.get("prix",a.get("price",a.get("montant","")))
                        titre=a.get("titre",a.get("title",a.get("libelle","")))
                        lieu=a.get("ville",a.get("city",a.get("localisation","")))
                        desc=a.get("description",a.get("texte",""))
                        ref=str(a.get("id",a.get("reference","")))
                        res.append({"lien":lien,"prix":str(prix),"titre":str(titre),"lieu":str(lieu),"description":str(desc),"ref":ref})
                    except:
                        continue
            log.info("API: "+str(len(res))+" annonces")
        except Exception as e:
            log.error("API error: "+str(e))
    return res

def gen_id(a):
    if a.get("ref"):
        return a["ref"]
    lien=a.get("lien","")
    m=re.search(r'r(\d+)$',lien)
    if m:
        return m.group(1)
    return hashlib.md5((lien or a.get("titre","")+a.get("prix","")).encode()).hexdigest()

def filtrer(a):
    texte=(str(a.get("titre",""))+str(a.get("description",""))+str(a.get("lieu",""))).lower()
    lien=a.get("lien","")
    px=prix_num(a.get("prix",""))
    raisons=[]
    arr=arr_depuis_texte(texte+lien,lien)
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
    if os.path.exists("annonces_vues.json"):
        os.remove("annonces_vues.json")
    return set()

def sauver(ids):
    with open(SEEN,"w") as f:
        json.dump({"ids":list(ids)},f)

def main():
    log.info("Demarrage PAP Parking API")
    telegram("PAP Alertes Parking demarre - API directe - toutes les 5 min")
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
                    +a.get("prix","")+" EUR\n"
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
