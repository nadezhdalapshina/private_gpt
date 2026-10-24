#!/usr/bin/env python3
"""Download candidate Wikimedia Commons photos into images/ and rewrite HTML.
Run with: python3 -m pip install requests beautifulsoup4 pillow && python3 fetch_photos.py
No bulk images are manually downloaded. Selection is heuristic; review PHOTO_REVIEW.csv.
"""
from pathlib import Path
from urllib.parse import urlparse
import csv, html, re, time, unicodedata, os
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

ROOT=Path(__file__).resolve().parent
HTML=ROOT/'index.html'
IMAGES=ROOT/'images'
IMAGES.mkdir(exist_ok=True)
API='https://commons.wikimedia.org/w/api.php'
# These files were confirmed mismatches in the initial run. Recheck on every run.
REJECT={2,13,15,52}
REFRESH=os.getenv('REFRESH_PHOTOS','0')=='1'
HEAD={'User-Agent':'SpainTripItineraryPhotoDownloader/1.0 (educational static itinerary; Wikimedia Commons API; contact: no-contact@example.org)'}
s=requests.Session();s.headers.update(HEAD)

def norm(t):
    t=unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()
    return set(re.findall(r'[a-z0-9]{3,}',t))-{'spain','spanish','photo','image','the','and','old','view','beautiful','scenic','inside','exterior'}

def fetch_candidates(query):
    params={'action':'query','generator':'search','gsrsearch':'filetype:bitmap '+query,'gsrnamespace':'6','gsrlimit':'30','prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':'1200','format':'json'}
    try:
        data=s.get(API,params=params,timeout=25);data.raise_for_status()
        pages=data.json().get('query',{}).get('pages',{})
        items=[]
        wanted=norm(query)
        for v in pages.values():
            info=(v.get('imageinfo') or [{}])[0]
            u=info.get('thumburl') or info.get('url','')
            if not u.startswith('https://') or not u.lower().split('?')[0].endswith(('.jpg','.jpeg','.png','.webp')):continue
            title=v.get('title','').removeprefix('File:')
            words=norm(title)
            coverage=len(wanted&words)/max(len(wanted),1)
            # Reject weak matches. A shared word like 'Malaga' is not sufficient.
            important=wanted-{'malaga','seville','sevilla','valencia','granada','spain','girona','ronda','cadaques','figueres','barcelona'}
            if important and not (words & important):continue
            if any(x in words for x in {'mural','graffiti','logo','coat','emblem','flag','poster','map','drawing'}):continue
            specificity=len(wanted&words)
            if info.get('width',0)<500:continue
            items.append((coverage,specificity,title,u,info))
        return sorted(items,key=lambda x:(x[0],x[1]),reverse=True)
    except Exception as e:
        print('Search error:',query,str(e)[:130]);return []

def save_image(url,path):
    r=s.get(url,timeout=30);r.raise_for_status()
    im=Image.open(BytesIO(r.content));im.load()
    if im.width<500 or im.height<260:raise ValueError('Too small')
    im=im.convert('RGB');im.thumbnail((1200,900))
    im.save(path,'WEBP',quality=83,method=5)

def main():
    soup=BeautifulSoup(HTML.read_text(encoding='utf-8'),'html.parser')
    all_cards=soup.select('article.spot')
    log=[];used=set();total=0
    for i,art in enumerate(all_cards,1):
        ph=art.select_one('.spot-photo');img=ph.select_one('img')
        title=art.select_one('h4').get_text(' ',strip=True)
        q=ph.get('data-search') or title
        target=IMAGES/f'place-{i:02d}.webp'
        if target.exists() and i not in REJECT and not REFRESH:
            img['src']=f'images/{target.name}';ph['data-photo-exact']='1';ph['data-photo-fallback']=''
            log.append([i,title,q,'already saved',f'images/{target.name}','',''])
            total+=1;continue
        candidates=fetch_candidates(q)
        # Heuristic: don't insert unrelated landscapes. Prefer score >=0.25 and no duplicates.
        chosen=None
        for c in candidates:
            coverage,match_count,name,url,info=c
            if coverage < .48 or match_count<2 or url in used:continue
            try:save_image(url,target)
            except Exception as e:continue
            chosen=c;used.add(url);break
        if chosen:
            coverage,_,name,url,info=chosen
            img['src']=f'images/{target.name}';ph['data-photo-exact']='1';ph['data-photo-fallback']=''
            # Attribution beneath the image, based on original Commons file page
            artist=info.get('extmetadata',{}).get('Artist',{}).get('value','')
            license_=info.get('extmetadata',{}).get('LicenseShortName',{}).get('value','')
            page='https://commons.wikimedia.org/wiki/File:'+name.replace(' ','_')
            existing=art.select_one('.photo-credit')
            if not existing:
                credit=soup.new_tag('small',attrs={'class':'photo-credit'})
                link=soup.new_tag('a',href=page,target='_blank',rel='noopener noreferrer');link.string=f'Фото: Wikimedia Commons · {license_}'
                credit.append(link);ph.insert_after(credit)
            log.append([i,title,q,f'{coverage:.2f}',f'images/{target.name}',page,re.sub('<[^>]+>','',artist)[:100]])
            total+=1
        else:
            # A previously rejected mismatched image must not remain linked as 'correct'.
            if i in REJECT and target.exists():
                target.unlink()
                img['src']=''
                ph['data-photo-exact']='0'
            # Leave original URL, but DO NOT substitute another landmark: manual review required.
            # The browser link to exact photo search remains available.
            log.append([i,title,q,'not found','', '', ''])
        print(f'{i:02d}/{len(all_cards)} {title}:', 'ok' if chosen else 'not found',flush=True)
        time.sleep(.12)
    # Remove old wrong fallback addresses, preserving the existing functionality.
    for ph in soup.select('.spot-photo'):
        ph['data-photo-fallback']=''
        if ph.get('data-photo-exact') != '1':ph['data-photo-exact']='0'
    HTML.write_text(str(soup),encoding='utf-8')
    with open(ROOT/'PHOTO_REVIEW.csv','w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['№','Место','Поисковый запрос','Совпадение по словам','Локальный файл','Источник фото','Автор']);writer.writerows(log)
    print(f'Done: {total}/{len(all_cards)} files present. Photo accuracy requires visual review; do not interpret name overlap as proof.')

if __name__=='__main__':main()
