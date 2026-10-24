#!/usr/bin/env python3
"""Download explicitly verified Wikimedia Commons images to local files.
Never pick another photo by word overlap. Does not touch unrelated cards.
"""
import io, os, time, hashlib
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image

ROOT=Path(__file__).resolve().parent
API="https://commons.wikimedia.org/w/api.php"
S=requests.Session()
S.headers.update({"User-Agent":"SpainTripPhotoCurator/2.0 (static travel itinerary; Wikimedia Commons attribution; github.com/nadezhdalapshina/private_gpt)"})
# Card position (1-based) -> exact Wikimedia Commons filename confirmed on file's description page.
CURATED={
    1:("Собор Жироны","Main facade of the Cathedral of Girona and stairs.jpg"),
    2:("Еврейский квартал","Girona - Call 02 2016-11-15.jpg"),
    3:("Крепостные стены","City walls of Girona (4).jpg"),
    4:("Улочки Кадакеса","Small street of Cadaques (4871795350).jpg"),
    5:("Бухта Портльигат","Port Lligat, Cadaqués (Gerona) - panoramio (2).jpg"),
    6:("Бухты и пляжи","Portlligat cadaques.jpg"),
    7:("Старые улочки","Small street of Cadaques (4871795350).jpg"),
}

def download_exact(filename):
    for attempt in range(5):
        data=S.get(API,params={
        "action":"query","titles":"File:"+filename,"prop":"imageinfo",
        "iiprop":"url|extmetadata|size","iiurlwidth":1200,"format":"json"
    },timeout=30)
        if data.status_code != 429:break
        time.sleep(8*(attempt+1))
    data.raise_for_status()
    pages=data.json().get("query",{}).get("pages",{})
    item=next(iter(pages.values()),{})
    ii=(item.get("imageinfo") or [None])[0]
    if not ii or not (ii.get("thumburl") or ii.get("url")):
        raise RuntimeError("Missing Commons original: "+filename)
    url=ii.get("thumburl") or ii["url"]
    response=S.get(url,timeout=45);response.raise_for_status()
    photo=Image.open(io.BytesIO(response.content));photo.load()
    if photo.width<500 or photo.height<260:
        raise RuntimeError("Photo too small: "+filename)
    photo=photo.convert("RGB");photo.thumbnail((1200,900))
    return photo,ii

def main():
    path=ROOT/"index.html"
    soup=BeautifulSoup(path.read_text(encoding="utf-8"),"html.parser")
    cards=soup.select("article.spot")
    assert len(cards)==64,(len(cards),"Unexpected number of cards")
    folder=ROOT/"images";folder.mkdir(exist_ok=True)
    changed=[]
    for i,(title,filename) in CURATED.items():
        matches=[card for card in cards if card.select_one('h4') and card.select_one('h4').get_text(' ',strip=True)==title]
        if len(matches)!=1:raise RuntimeError('Card not uniquely found: '+title)
        art=matches[0]
        img=art.select_one(".spot-photo img")
        ph=art.select_one(".spot-photo")
        if not img or not ph:raise RuntimeError("Card photo markup missing: "+str(i))
        try:
            pic,ii=download_exact(filename)
        except Exception as e:
            print("Skipped",i,filename,repr(e),flush=True)
            continue
        output=folder/("place-%02d.webp"%i)
        pic.save(output,"WEBP",quality=84,method=5)
        img["src"]="images/"+output.name+"?v="+hashlib.sha256(output.read_bytes()).hexdigest()[:12]
        ph["data-photo-exact"]="1"
        ph["data-photo-fallback"]=""
        ph["data-photo-source"]="curated-commons"
        # Keep credit to the original Commons file page visible beneath image.
        credit=art.select_one(".photo-credit")
        if credit is None:
            credit=soup.new_tag("small",attrs={"class":"photo-credit"})
            ph.insert_after(credit)
        credit.clear()
        link=soup.new_tag("a",href=ii.get("descriptionurl","https://commons.wikimedia.org/wiki/File:"+filename.replace(" ","_")),target="_blank",rel="noopener noreferrer")
        meta=ii.get("extmetadata") or {}
        license_name=meta.get("LicenseShortName",{}).get("value","Wikimedia Commons")
        link.string="Фото: Wikimedia Commons · "+license_name
        credit.append(link)
        changed.append((i,art.select_one("h4").get_text(" ",strip=True),filename))
        print("Updated",i,filename,flush=True)
        time.sleep(2)
    if not changed:raise RuntimeError("No images successfully updated; leaving HTML unchanged")
    path.write_text(str(soup),encoding="utf-8")
    print("Curated update:",len(changed),"of",len(CURATED),flush=True)

if __name__=="__main__":main()
