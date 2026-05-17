#!/usr/bin/env python3
"""
DEEP STATE — Submarine OSINT Scraper v3
Scrapes RSS feeds AND generates per-submarine enriched sightings.
Run with:  python3 scraper.py           (once)
           python3 scraper.py --loop    (every 30 min)
"""
import feedparser, requests, json, re, time, os, random
from datetime import datetime, timezone
from bs4 import BeautifulSoup

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sightings.json")

RSS_FEEDS = [
    {"name":"USNI News",       "url":"https://news.usni.org/feed",         "priority":3},
    {"name":"USNI Fleet",      "url":"https://news.usni.org/category/fleet-tracker/feed","priority":3},
    {"name":"USNI W.Pac Pulse","url":"https://news.usni.org/category/news/western-pacific-pulse/feed","priority":3},
    {"name":"Naval News",      "url":"https://www.navalnews.com/feed/",     "priority":2},
    {"name":"HI Sutton",       "url":"https://www.hisutton.com/feed.xml",   "priority":2},
    {"name":"Naval Today",     "url":"https://navaltoday.com/feed/",       "priority":2},
    {"name":"Defense News",    "url":"https://www.defensenews.com/feed/",  "priority":1},
]

SUB_KEYWORDS = [
    'submarine','ssn ','ssbn','ssgn','submarin','submerged','underwater',
    'ohio class','virginia class','seawolf','astute class','vanguard class',
    'borei','yasen','kilo class','improved kilo','oscar class','belgorod',
    'poseidon','bulava','trident','slbm','ballistic missile sub',
    'nuclear submarine','diesel submarine','attack submarine','aukus',
    'snle','sna barracuda','triomphant','suffren','arihant',
    'gotland','collins class','soryu','taigei','kss-iii',
    'type 214','type 212','type 093','type 094','type 039',
    'jin class','shang class','anti-submarine','asw patrol',
    'submarine spotted','submarine port','sub tender',
]

SEA_COORDS = {
    "north pacific":(45.,-160.),"south pacific":(-20.,-140.),
    "pacific ocean":(10.,-150.),"western pacific":(20.,140.),
    "north atlantic":(55.,-30.),"south atlantic":(-25.,-20.),
    "atlantic ocean":(30.,-40.),"indian ocean":(-15.,75.),
    "arctic ocean":(80.,15.),"arctic":(80.,15.),
    "south china sea":(14.,114.),"east china sea":(28.,125.),
    "sea of japan":(39.,135.),"sea of okhotsk":(55.,148.),
    "philippine sea":(16.,130.),"arabian sea":(17.,63.),
    "persian gulf":(27.,52.),"gulf of oman":(23.,58.),
    "strait of hormuz":(26.5,56.5),"red sea":(20.,38.),
    "mediterranean sea":(36.,18.),"mediterranean":(36.,18.),
    "black sea":(43.,34.),"baltic sea":(58.,20.),"north sea":(57.,3.),
    "barents sea":(73.,35.),"norwegian sea":(68.,5.),
    "bay of bengal":(14.,88.),"andaman sea":(11.,97.),
    "coral sea":(-18.,152.),"tasman sea":(-40.,160.),
    "caribbean":(16.,-75.),"gulf of mexico":(24.,-90.),
    "bering sea":(57.,-175.),"yellow sea":(35.,123.),
    "aegean sea":(39.,25.),"tyrrhenian sea":(40.,12.),
    "english channel":(50.,-1.),"giuk gap":(64.,-18.),
    "tsushima strait":(34.5,129.2),"taiwan strait":(24.5,119.5),
    # Ports & Bases
    "norfolk":(36.9,-76.3),"kitsap":(47.6,-122.6),"bangor":(47.7,-122.7),
    "groton":(41.4,-72.1),"pearl harbor":(21.4,-157.9),
    "guam":(13.4,144.6),"yokosuka":(35.3,139.7),"busan":(35.1,129.0),
    "faslane":(56.1,-4.7),"clyde":(55.9,-4.8),"devonport":(50.4,-4.2),
    "brest":(48.4,-4.5),"île longue":(48.3,-4.5),"toulon":(43.1,5.9),
    "severomorsk":(69.1,33.5),"gadjievo":(69.2,33.2),
    "olenya":(69.2,33.2),"olenya guba":(69.2,33.2),
    "vladivostok":(43.1,132.0),"vilyuchinsk":(52.9,158.4),
    "yulin":(18.2,109.5),"sanya":(18.2,109.5),"qingdao":(36.1,120.3),
    "karachi":(24.8,67.0),"visakhapatnam":(17.7,83.3),
    "cam ranh":(11.9,109.2),"kiel":(54.3,10.2),"bergen":(60.4,5.3),
    "karlskrona":(56.2,15.6),"kronstadt":(60.0,29.8),
    "st petersburg":(59.95,30.32),"saint petersburg":(59.95,30.32),
    "piraeus":(37.9,23.7),"augusta":(37.2,15.2),"rota":(36.6,-6.3),
    "cartagena":(37.6,-0.9),"gdynia":(54.5,18.5),
    "sinpo":(40.0,128.2),"wonsan":(39.2,127.4),
    "stirling":(-32.2,115.7),"rockingham":(-32.2,115.7),
    "itaguai":(-22.8,-43.8),"portsmouth":(50.8,-1.1),
    "bahrain":(26.2,50.6),"djibouti":(11.6,43.1),
    "diego garcia":(-7.3,72.4),"naples":(40.8,14.2),
    "murmansk":(68.9,33.1),"arkhangelsk":(64.5,40.5),
    "reykjavik":(64.15,-21.9),"iceland":(64.5,-18.0),
}

# Per-submarine baseline positions (last known / estimated)
SUB_BASELINES = {
    "uss_ohio":    {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.70,"lon":-122.70},
    "uss_mich":    {"loc":"Busan, South Korea","lat":35.08,"lon":129.04},
    "uss_virginia":{"loc":"Naval Station Norfolk, Virginia","lat":36.93,"lon":-76.31},
    "uss_ndakota": {"loc":"GIUK Gap, North Atlantic","lat":62.8,"lon":-21.5},
    "uss_seawolf": {"loc":"NSWC Kitsap, Washington","lat":47.72,"lon":-122.41},
    "uss_jcarter": {"loc":"NSWC Kitsap, Washington","lat":47.56,"lon":-122.61},
    "rus_yuri":    {"loc":"Barents Sea, Gadzhievo","lat":72.5,"lon":28.0},
    "rus_vlad":    {"loc":"Vilyuchinsk, Pacific","lat":52.9,"lon":158.4},
    "rus_sev":     {"loc":"Barents Sea, Severomorsk","lat":70.5,"lon":36.0},
    "rus_kazan":   {"loc":"Norwegian Sea","lat":69.0,"lon":16.0},
    "rus_belg":    {"loc":"Olenya Guba, Barents","lat":69.2,"lon":33.8},
    "rus_kilo":    {"loc":"Black Sea","lat":44.6,"lon":33.5},
    "rus_orel":    {"loc":"Severomorsk, Russia","lat":69.07,"lon":33.42},
    "chn_jin":     {"loc":"Yulin Base, Hainan","lat":18.2,"lon":109.55},
    "chn_shang":   {"loc":"South China Sea","lat":16.0,"lon":114.5},
    "gbr_vanguard":{"loc":"HMNB Clyde, Faslane","lat":55.92,"lon":-4.75},
    "gbr_astute":  {"loc":"Gulf of Oman","lat":22.8,"lon":58.5},
    "fra_triomphant":{"loc":"Île Longue, Brest","lat":48.36,"lon":-4.46},
    "fra_terrible":{"loc":"North Atlantic (ZOSTRAN)","lat":48.5,"lon":-18.0},
    "fra_suffren": {"loc":"Naval Base Toulon","lat":43.11,"lon":5.92},
    "ind_arihant": {"loc":"Bay of Bengal","lat":15.0,"lon":83.5},
    "deu_u32":     {"loc":"Baltic Sea, Kiel","lat":55.5,"lon":12.5},
    "jpn_soryu":   {"loc":"Tsushima Strait","lat":35.0,"lon":130.0},
    "kor_dosan":   {"loc":"Yellow Sea","lat":36.0,"lon":124.0},
    "prk_hero":    {"loc":"Sinpo, DPRK","lat":40.02,"lon":128.20},
    "irn_fateh":   {"loc":"Strait of Hormuz","lat":26.55,"lon":56.25},
    "tur_preveze": {"loc":"Aegean Sea","lat":38.5,"lon":26.0},
    "aus_collins": {"loc":"HMAS Stirling, Perth","lat":-32.18,"lon":115.68},
    "can_victoria": {"loc":"Victoria, Canada","lat":48.43,"lon":-123.37},
    "nld_dolfijn": {"loc":"Den Helder, Netherlands","lat":52.96,"lon":4.75},
    "ita_todaro":  {"loc":"Augusta, Sicily","lat":37.22,"lon":15.22},
    "esp_isaac":   {"loc":"Cartagena, Spain","lat":37.60,"lon":-0.98},
    "nor_utsira":  {"loc":"North Sea","lat":61.0,"lon":3.0},
    "swe_gotland": {"loc":"Baltic Sea, Karlskrona","lat":56.2,"lon":15.5},
    "grc_papa":    {"loc":"Aegean Sea, Salamis","lat":37.95,"lon":23.6},
    "bra_riachuelo":{"loc":"Itaguaí, Rio de Janeiro","lat":-22.87,"lon":-43.80},
    "pak_hamza":   {"loc":"Arabian Sea, Karachi","lat":24.0,"lon":63.0},
    "vnm_hanoi":   {"loc":"Cam Ranh Bay, Vietnam","lat":11.90,"lon":109.22},
    "dza_rais":    {"loc":"Western Mediterranean","lat":37.2,"lon":2.5},
}

SUB_NAME_MAP = {
    "uss ohio":"uss_ohio","ssbn-726":"uss_ohio",
    "uss michigan":"uss_mich","ssgn-727":"uss_mich",
    "uss virginia":"uss_virginia","ssn-774":"uss_virginia",
    "uss north dakota":"uss_ndakota","ssn-784":"uss_ndakota",
    "uss seawolf":"uss_seawolf","ssn-21":"uss_seawolf",
    "uss jimmy carter":"uss_jcarter","ssn-23":"uss_jcarter",
    "uss newport news":"uss_seawolf",
    "yuri dolgoruky":"rus_yuri","k-535":"rus_yuri",
    "vladimir monomakh":"rus_vlad","k-551":"rus_vlad",
    "petropavlovsk":"rus_vlad",
    "severodvinsk":"rus_sev","k-329 sev":"rus_sev",
    "kazan":"rus_kazan","k-561":"rus_kazan",
    "belgorod":"rus_belg",
    "novorossiysk":"rus_kilo","b-261":"rus_kilo","kilo class":"rus_kilo",
    "orel":"rus_orel","k-266":"rus_orel",
    "long march 17":"chn_jin","jin class":"chn_jin","type 094":"chn_jin",
    "long march 11":"chn_shang","shang class":"chn_shang","type 093":"chn_shang",
    "hms vanguard":"gbr_vanguard","s28":"gbr_vanguard","vanguard class":"gbr_vanguard",
    "hms astute":"gbr_astute","s119":"gbr_astute","astute class":"gbr_astute",
    "le triomphant":"fra_triomphant","s616":"fra_triomphant","triomphant":"fra_triomphant",
    "le terrible":"fra_terrible","s619":"fra_terrible",
    "suffren":"fra_suffren","barracuda":"fra_suffren",
    "ins arihant":"ind_arihant","ins aridhaman":"ind_arihant","arihant":"ind_arihant",
    "u-32":"deu_u32","type 212":"deu_u32",
    "soryu":"jpn_soryu","js soryu":"jpn_soryu","sōryū":"jpn_soryu",
    "dosan ahn":"kor_dosan","kss-iii":"kor_dosan",
    "hero kim":"prk_hero","kim kun ok":"prk_hero","sinpo":"prk_hero",
    "iris fateh":"irn_fateh","fateh class":"irn_fateh","ghadir":"irn_fateh",
    "tcg preveze":"tur_preveze","type 209":"tur_preveze",
    "hmas collins":"aus_collins","collins class":"aus_collins",
    "hmcs victoria":"can_victoria","victoria class":"can_victoria",
    "hnlms dolfijn":"nld_dolfijn","dolfijn":"nld_dolfijn","walrus class":"nld_dolfijn",
    "its todaro":"ita_todaro",
    "isaac peral":"esp_isaac","s-80":"esp_isaac",
    "hnoMs utsira":"nor_utsira","ula class":"nor_utsira",
    "gotland":"swe_gotland","hswms":"swe_gotland",
    "papanikolis":"grc_papa","type 214":"grc_papa",
    "riachuelo":"bra_riachuelo","scorpene":"bra_riachuelo",
    "pns hamza":"pak_hamza","agosta":"pak_hamza",
    "ha noi":"vnm_hanoi","hq-182":"vnm_hanoi",
    "rais hadj":"dza_rais",
}

def is_sub_article(title, summary):
    text=(title+" "+summary).lower()
    return any(k in text for k in SUB_KEYWORDS)

def extract_sea_location(text):
    text_l=text.lower()
    best=None; best_len=0
    for name,coords in SEA_COORDS.items():
        if name in text_l and len(name)>best_len:
            best=(name,coords); best_len=len(name)
    return best

def extract_sub_id(text):
    text_l=text.lower()
    for name,sid in SUB_NAME_MAP.items():
        if name in text_l:
            return sid,name
    return None,None

def clean_html(text):
    try: return BeautifulSoup(text,'lxml').get_text(separator=' ')
    except: return re.sub(r'<[^>]+>',' ',text)


def fetch_article_text(url):
    headers={
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36'
    }
    try:
        resp=requests.get(url,headers=headers,timeout=12)
        if resp.status_code!=200:
            return ''
        soup=BeautifulSoup(resp.text,'lxml')
        article=soup.find('article')
        if article:
            text=article.get_text(' ')
        else:
            paragraphs=[p.get_text(' ') for p in soup.find_all('p')]
            text=' '.join(paragraphs)
        return re.sub(r'\s+',' ',text).strip()
    except Exception:
        return ''


def fetch_feed(cfg):
    try: return feedparser.parse(cfg["url"]).entries
    except Exception as e: print(f"  ✗ {cfg['name']}: {e}"); return []

def scrape_live():
    """Scrape live RSS feeds for fresh sightings."""
    sightings=[]; seen=set()
    print(f"\n{'='*55}")
    print(f"DEEP STATE SCRAPER v3 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*55}")

    for cfg in RSS_FEEDS:
        print(f"\n📡 {cfg['name']}...")
        entries=fetch_feed(cfg)
        print(f"   {len(entries)} articles")
        for entry in entries:
            title=clean_html(entry.get("title",""))
            summary=clean_html(entry.get("summary","") or entry.get("description",""))
            link=entry.get("link","")
            pub=entry.get("published",entry.get("updated",""))
            content=''
            if entry.get('content'):
                content_item=entry.get('content')
                if isinstance(content_item, list) and content_item:
                    content=clean_html(content_item[0].get('value',''))
                elif isinstance(content_item, dict):
                    content=clean_html(content_item.get('value',''))
            text=title+" "+summary+" "+content
            if not is_sub_article(title,summary) and not is_sub_article(title,content):
                continue
            uid=link or title
            if uid in seen: continue
            seen.add(uid)
            if not link and content:
                link=entry.get('id','') or ''
            sub_id,sub_name=extract_sub_id(text)
            loc=extract_sea_location(text)
            if (not loc or not sub_id) and link:
                article_text=fetch_article_text(link)
                if article_text:
                    if not sub_id:
                        sub_id,sub_name=extract_sub_id(article_text)
                    if not loc:
                        loc=extract_sea_location(article_text)
            if loc:
                loc_name,(lat,lon)=loc
                lat+=random.uniform(-0.8,0.8); lon+=random.uniform(-0.8,0.8)
            elif sub_id and sub_id in SUB_BASELINES:
                b=SUB_BASELINES[sub_id]
                loc_name=b["loc"]
                lat=b["lat"]+random.uniform(-0.5,0.5)
                lon=b["lon"]+random.uniform(-0.5,0.5)
            else:
                lat=lon=None; loc_name="Position non confirmée"

            s={
                "id":uid,"sub_id":sub_id,"sub_name":sub_name,
                "title":title,"summary":summary[:600],
                "source":cfg["name"],"source_url":link,
                "location":loc_name.title() if loc_name else "Position Unconfirmed",
                "lat":round(lat,3) if lat else None,
                "lon":round(lon,3) if lon else None,
                "published":pub,
                "scraped_at":datetime.now(timezone.utc).isoformat(),
                "priority":cfg["priority"],
            }
            sightings.append(s)
            icon="☢" if sub_id else "📰"
            print(f"   {icon} [{sub_id or 'GEN'}] {title[:55]}")
            if lat: print(f"       📍 {loc_name} ({lat:.1f},{lon:.1f})")

    return sightings

def generate_baseline_sightings(live_sightings):
    """
    For each submarine with no live sighting yet,
    generate a baseline sighting from SUB_BASELINES.
    This ensures every submarine has at least one marker.
    """
    covered={s["sub_id"] for s in live_sightings if s["sub_id"]}
    baseline=[]
    now=datetime.now(timezone.utc).isoformat()

    for sub_id,b in SUB_BASELINES.items():
        if sub_id in covered: continue
        lat=b["lat"]+random.uniform(-0.3,0.3)
        lon=b["lon"]+random.uniform(-0.3,0.3)
        baseline.append({
            "id":f"baseline_{sub_id}",
            "sub_id":sub_id,"sub_name":sub_id.replace("_"," ").upper(),
            "title":f"Position estimée — {b['loc']}",
            "title_en":f"Estimated Position — {b['loc']}",
            "summary":"Position de base estimée pour ce sous-marin selon les dernières données publiques (IISS Military Balance 2025, sources OSINT). Cette position est approximative et basée sur le port d'attache ou la zone de patrouille connue.",
            "summary_en":f"Estimated baseline position for this submarine based on latest public data (IISS Military Balance 2025, OSINT sources). This position is approximate and based on the known homeport or patrol area.",
            "source":"IISS Military Balance 2025 / OSINT","source_url":"https://www.iiss.org",
            "location":b["loc"],
            "location_en":b["loc"],
            "lat":round(lat,3),"lon":round(lon,3),
            "published":now,"scraped_at":now,"priority":1,
        })
        print(f"   📌 Baseline: {sub_id} → {b['loc']}")

    return baseline

# ─── PATCH: update_sub_positions ─────────────────────────────────────────────
def update_sub_positions_in_html(sightings, html_path):
    """
    When a live sighting has a sub_id + coordinates,
    update that submarine's lat/lon in the sightings.json
    so the frontend can apply updated positions.
    Returns a dict: sub_id -> most-recent sighting dict
    """
    updates = {}
    for sg in sightings:
        if not sg.get('sub_id') or sg.get('lat') is None:
            continue
        sid = sg['sub_id']
        cur = updates.get(sid)
        if cur is None:
            updates[sid] = sg
        else:
            # Keep most recent
            try:
                d_new = datetime.fromisoformat(sg.get('published','').replace('Z','+00:00').split(',')[-1].strip() if ',' in sg.get('published','') else sg.get('published','2000-01-01'))
            except:
                d_new = datetime(2000,1,1,tzinfo=timezone.utc)
            try:
                d_cur = datetime.fromisoformat(cur.get('published','').replace('Z','+00:00').split(',')[-1].strip() if ',' in cur.get('published','') else cur.get('published','2000-01-01'))
            except:
                d_cur = datetime(2000,1,1,tzinfo=timezone.utc)
            if d_new > d_cur:
                updates[sid] = sg

    if updates:
        print(f"\n📍 Position updates found for {len(updates)} submarines:")
        for sid, sg in updates.items():
            print(f"   {sid} → {sg['location']} ({sg['lat']:.2f}, {sg['lon']:.2f}) [{sg['source']}]")
    return updates

def run_once():
    live=scrape_live()
    print(f"\n📌 Génération baselines pour sous-marins sans signalement...")
    # Track which subs got live position updates (most recent per sub)
    position_updates = update_sub_positions_in_html(live, OUTPUT_FILE)
    baselines=generate_baseline_sightings(live)
    all_sightings=live+baselines
    all_sightings.sort(key=lambda x:(x["priority"],x.get("published","")),reverse=True)
    # Load existing data to preserve position_updates history
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as ef:
                existing = json.load(ef)
        except Exception:
            existing = {}

    prev_pos = existing.get('position_updates', {}) or {}
    # Normalize previous format: if an entry is a single dict, convert to list
    for k, v in list(prev_pos.items()):
        if isinstance(v, dict):
            prev_pos[k] = [v]

    # Append new updates to history lists when changed/new
    for sid, sg in position_updates.items():
        entry = {
            'lat': sg['lat'], 'lon': sg['lon'],
            'location': sg.get('location'), 'source': sg.get('source'),
            'title': sg.get('title'), 'source_url': sg.get('source_url'),
            'published': sg.get('published'),
            'recorded_at': datetime.now(timezone.utc).isoformat()
        }
        lst = prev_pos.get(sid, [])
        last = lst[-1] if lst else None
        if not last or last.get('published') != entry.get('published') or last.get('lat') != entry.get('lat') or last.get('lon') != entry.get('lon'):
            lst.append(entry)
            prev_pos[sid] = lst

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "count": len(all_sightings),
        "live_count": len(live),
        "baseline_count": len(baselines),
        "position_updates": prev_pos,
        "sightings": all_sightings
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ {len(live)} live + {len(baselines)} baselines = {len(all_sightings)} total")
    print(f"📍 {len(position_updates)} submarine positions updated from live data (history appended)")
    print(f"💾 {OUTPUT_FILE}")
    return data

def run_loop(interval_minutes=30):
    print(f"🔄 Loop every {interval_minutes}min — Ctrl+C to stop")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"❌ {e}")
        time.sleep(interval_minutes*60)

if __name__=="__main__":
    import sys
    if "--loop" in sys.argv: run_loop(30)
    else: run_once()

