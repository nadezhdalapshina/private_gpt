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
    45:"Coves de sant Josep de la Vall d'Uixó, barques.JPG",
    46:"Interior de les coves de sant Josep, zona seca.JPG",
    47:"Vista del paratge de les coves de sant Josep des de la muntanyeta.JPG",
    48:"Vista de les muntanyes dels voltants de les coves de sant Josep, la Vall d'Uixó.JPG",
    49:"Jardín del Turia.JPG",
    50:"Ciudad de las Artes y las Ciencias in Valencia, Spain.jpg",
    51:"Palau de les Arts Reina Sofia 01.jpg",
    52:"Valencia - Beach 01.jpg",
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
    assert len(cards)==68,(len(cards),"Unexpected number of cards")
    folder=ROOT/"images";folder.mkdir(exist_ok=True)
    changed=[]
    for i,filename in CURATED.items():
        art=cards[i-1]
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
