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
    # ── Tier 1: Naval spécialisé ──────────────────────────────────────
    {"name":"USNI News",        "url":"https://news.usni.org/feed",                                           "priority":3},
    {"name":"USNI Fleet",       "url":"https://news.usni.org/category/fleet-tracker/feed",                    "priority":3},
    {"name":"USNI W.Pac Pulse", "url":"https://news.usni.org/category/news/western-pacific-pulse/feed",       "priority":3},
    {"name":"Naval News",       "url":"https://www.navalnews.com/feed/",                                      "priority":3},
    {"name":"HI Sutton",        "url":"https://www.hisutton.com/feed.xml",                                    "priority":3},
    {"name":"Naval Today",      "url":"https://navaltoday.com/feed/",                                         "priority":2},
    # ── Tier 2: Défense & OSINT ───────────────────────────────────────
    {"name":"The War Zone",     "url":"https://www.thedrive.com/the-war-zone/feed",                           "priority":2},
    {"name":"Breaking Defense", "url":"https://breakingdefense.com/feed/",                                    "priority":2},
    {"name":"Defense News",     "url":"https://www.defensenews.com/arc/outboundfeeds/rss/",                   "priority":2},
    {"name":"Bellingcat",       "url":"https://www.bellingcat.com/feed/",                                     "priority":2},
    {"name":"War on the Rocks", "url":"https://warontherocks.com/feed/",                                      "priority":1},
    {"name":"IISS",             "url":"https://www.iiss.org/feeds/analysis",                                  "priority":1},
    # ── Tier 3: YouTube (RSS natif) ───────────────────────────────────
    {"name":"YouTube NavalNews","url":"https://www.youtube.com/feeds/videos.xml?channel_id=UCPZIpjVb7oCHpFpB5R9BVJA","priority":1},
    {"name":"YouTube HI Sutton","url":"https://www.youtube.com/feeds/videos.xml?channel_id=UCGkEnFYi1lbC2RHuasMQXdA","priority":1},
    {"name":"YouTube NavInst",  "url":"https://www.youtube.com/feeds/videos.xml?channel_id=UC0hnOEj_nFdENjPvPbHhT3A","priority":1},
]

# Subreddits à surveiller
REDDIT_SUBS = [
    'submarines', 'navy', 'OSINT', 'geopolitics',
    'NavalNews', 'CredibleDefense', 'worldnews', 'military',
    'GlobalPowers', 'IntelligenceCommunity',
]

# Canaux Telegram publics (web preview t.me/s/)
TELEGRAM_CHANNELS = [
    'warshipcam',       # photos de navires / sightings
    'navaltoday',       # Naval Today
    'navalnewscom',     # Naval News
    'defmon3',          # Defence Monitor
    'modwatch',         # Ministry of Defence watch
    'operationswatch',  # opérations militaires
    'rybar_en',         # OSINT military (EN)
    'bulvar_media',     # OSINT naval
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
    "gbr_astute":  {"loc":"Gulf of Oman","lat":24.5,"lon":57.5},
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
    "ita_todaro":  {"loc":"Augusta, Sicily","lat":37.00,"lon":15.50},
    "esp_isaac":   {"loc":"Cartagena, Spain","lat":37.60,"lon":-0.98},
    "nor_utsira":  {"loc":"North Sea","lat":61.0,"lon":3.0},
    "swe_gotland": {"loc":"Baltic Sea, Karlskrona","lat":56.2,"lon":15.5},
    "grc_papa":    {"loc":"Aegean Sea, Salamis","lat":37.95,"lon":23.6},
    "bra_riachuelo":{"loc":"Itaguaí, Rio de Janeiro","lat":-22.87,"lon":-43.80},
    "pak_hamza":   {"loc":"Arabian Sea, Karachi","lat":24.0,"lon":63.0},
    "vnm_hanoi":   {"loc":"Cam Ranh Bay, Vietnam","lat":11.90,"lon":109.22},
    "dza_rais":    {"loc":"Western Mediterranean","lat":37.2,"lon":2.5},
    # USA - additional
    "uss_tenn":     {"loc":"Kings Bay, Georgia","lat":30.60,"lon":-80.80},
    "uss_kentucky": {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.73,"lon":-122.76},
    "uss_connecticut":{"loc":"NSWC Kitsap, Bremerton","lat":47.57,"lon":-122.64},
    "uss_springfield":{"loc":"Pearl Harbor, Hawaii","lat":21.36,"lon":-157.97},
    "uss_hawaii":   {"loc":"Pearl Harbor, Hawaii","lat":21.35,"lon":-157.96},
    "uss_minnesota":{"loc":"Naval Station Norfolk, Virginia","lat":36.85,"lon":-76.30},
    "uss_delaware": {"loc":"Naval Station Norfolk, Virginia","lat":36.84,"lon":-76.29},
    # Russia - additional
    "rus_tula":     {"loc":"Barents Sea, Gadzhievo","lat":69.51,"lon":32.93},
    "rus_karelia":  {"loc":"Barents Sea, Gadzhievo","lat":69.48,"lon":33.01},
    "rus_nevsky":   {"loc":"Vilyuchinsk, Pacific","lat":52.94,"lon":158.71},
    "rus_knyaz":    {"loc":"Barents Sea, Gadzhievo","lat":69.10,"lon":33.20},
    "rus_rostov":   {"loc":"Vladivostok, Pacific Fleet","lat":52.95,"lon":158.60},
    "rus_krasno":   {"loc":"Barents Sea, Severomorsk","lat":69.12,"lon":33.48},
    "rus_tver":     {"loc":"Rybachiy, Pacific Fleet","lat":52.95,"lon":158.68},
    # China - additional
    "chn_yuan1":    {"loc":"Yulin Base, Hainan","lat":18.22,"lon":109.48},
    "chn_yuan2":    {"loc":"South China Sea","lat":20.10,"lon":110.20},
    "chn_jin2":     {"loc":"Yulin Base, Hainan","lat":18.20,"lon":109.52},
    "chn_shang2":   {"loc":"South China Sea","lat":22.30,"lon":114.18},
    "chn_song":     {"loc":"East China Sea","lat":25.10,"lon":121.70},
    # UK - additional
    "gbr_victorious":{"loc":"North Atlantic, CASD Patrol","lat":52.00,"lon":-20.00},
    "gbr_vigilant": {"loc":"HMNB Clyde, Faslane","lat":56.02,"lon":-4.87},
    "gbr_ambush":   {"loc":"Mediterranean Sea","lat":38.00,"lon":8.00},
    "gbr_audacious":{"loc":"HMNB Clyde, Faslane","lat":56.05,"lon":-4.78},
    # France - additional
    "fra_vigilant": {"loc":"North Atlantic (FOST patrol)","lat":46.50,"lon":-14.80},
    "fra_temeraire":{"loc":"Île Longue, Brest","lat":48.32,"lon":-4.52},
    "fra_duguay":   {"loc":"Naval Base Toulon","lat":43.14,"lon":5.95},
    # India - additional
    "ind_aridhaman":{"loc":"Bay of Bengal, Visakhapatnam","lat":17.65,"lon":83.30},
    "ind_chakra":   {"loc":"Arabian Sea, Karwar","lat":13.50,"lon":72.50},
    "ind_sindhughost":{"loc":"Arabian Sea, Mumbai","lat":18.92,"lon":72.82},
    # Netherlands - additional
    "nld_walrus":   {"loc":"Den Helder, Netherlands","lat":52.96,"lon":4.75},
    "nld_bruinvis": {"loc":"Den Helder, Netherlands","lat":52.97,"lon":4.77},
    # Canada
    "can_cornerbrook":{"loc":"CFB Esquimalt, British Columbia","lat":48.44,"lon":-123.45},
    "can_windsor":  {"loc":"Halifax, Nova Scotia","lat":44.66,"lon":-63.57},
    # Chile
    "chl_carrera":  {"loc":"Talcahuano, Chile","lat":-36.50,"lon":-74.00},
    "chl_ohiggins": {"loc":"Talcahuano, Chile","lat":-36.70,"lon":-74.20},
    # Israel
    "isr_leviathan":{"loc":"Eastern Mediterranean","lat":32.80,"lon":34.50},
    "isr_tanin":    {"loc":"Eastern Mediterranean","lat":32.60,"lon":34.40},
    # Singapore
    "sgp_impeccable":{"loc":"Strait of Malacca, Singapore","lat":1.28,"lon":103.78},
    "sgp_stalwart": {"loc":"Strait of Malacca, Singapore","lat":1.30,"lon":103.80},
    # Malaysia
    "mys_razak":    {"loc":"South China Sea, Kota Kinabalu","lat":5.00,"lon":118.00},
    # Portugal
    "prt_tridente": {"loc":"Setubal, Portugal","lat":38.52,"lon":-8.88},
    # South Korea - additional
    "kor_yisunshin":{"loc":"Sea of Japan, Jinhae","lat":35.00,"lon":129.30},
    "kor_sonwonil": {"loc":"Sea of Japan, Jinhae","lat":34.80,"lon":129.00},
    # Taiwan
    "twn_hailung":  {"loc":"Philippine Sea, Taiwan","lat":23.50,"lon":122.00},
    "twn_haikun":   {"loc":"Philippine Sea, Taiwan","lat":23.70,"lon":122.20},
    # Egypt
    "egy_s44":      {"loc":"Eastern Mediterranean","lat":32.00,"lon":29.00},
    # Argentina
    "arg_santacruz":{"loc":"South Atlantic, Mar del Plata","lat":-38.50,"lon":-58.50},
    # Peru
    "per_pisagua":  {"loc":"South Pacific, Callao","lat":-11.50,"lon":-78.50},
    # Colombia
    "col_tayrona":  {"loc":"Caribbean Sea, Cartagena","lat":11.00,"lon":-76.50},
    # Venezuela
    "ven_sabalo":   {"loc":"Caribbean Sea, Puerto Cabello","lat":11.50,"lon":-67.50},
    # Turkey - additional
    "tur_sakarya":  {"loc":"Golcuk, Sea of Marmara","lat":40.72,"lon":29.91},
    "tur_pirireis": {"loc":"Izmit, Turkey","lat":40.64,"lon":30.38},
    # Greece - additional
    "grc_matrozos": {"loc":"Aegean Sea, Salamis","lat":37.95,"lon":23.48},
    # Australia - additional
    "aus_farncomb": {"loc":"Spencer Gulf, Adelaide","lat":-34.84,"lon":138.58},
    # Japan - additional
    "jpn_oyashio":  {"loc":"Pacific Ocean, Kure","lat":34.20,"lon":132.50},
    "jpn_taigei":   {"loc":"Pacific, Yokosuka","lat":35.45,"lon":139.63},
    # Germany - additional
    "deu_u34":      {"loc":"Baltic Sea, Kiel","lat":54.31,"lon":10.14},
    # Sweden - additional
    "swe_sodermanland":{"loc":"Baltic Sea, Karlskrona","lat":59.00,"lon":18.50},
    # Norway - additional
    "nor_utvaer":   {"loc":"North Sea, Bergen","lat":60.42,"lon":5.35},
    # USA Ohio SSGNs
    "uss_florida":  {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.76,"lon":-122.74},
    "uss_georgia":  {"loc":"Kings Bay, Georgia","lat":30.79,"lon":-81.50},
    # USA Ohio SSBNs
    "uss_jackson":  {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.74,"lon":-122.77},
    "uss_alabama":  {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.78,"lon":-122.75},
    "uss_alaska":   {"loc":"Kings Bay, Georgia","lat":30.77,"lon":-81.52},
    "uss_nevada":   {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.80,"lon":-122.73},
    "uss_pennsylvania":{"loc":"NSWC Kitsap-Bangor, Washington","lat":47.76,"lon":-122.76},
    "uss_westva":   {"loc":"Kings Bay, Georgia","lat":30.80,"lon":-81.49},
    "uss_maryland": {"loc":"Kings Bay, Georgia","lat":30.82,"lon":-81.51},
    "uss_nebraska": {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.77,"lon":-122.71},
    "uss_rhodeisland":{"loc":"Kings Bay, Georgia","lat":30.78,"lon":-81.53},
    "uss_maine":    {"loc":"NSWC Kitsap-Bangor, Washington","lat":47.81,"lon":-122.74},
    "uss_wyoming":  {"loc":"Kings Bay, Georgia","lat":30.75,"lon":-81.51},
    "uss_louisiana":{"loc":"NSWC Kitsap-Bangor, Washington","lat":47.75,"lon":-122.79},
    # USA Virginia-class additional
    "uss_texas":    {"loc":"Pearl Harbor, Hawaii","lat":21.36,"lon":-157.98},
    "uss_northcarolina":{"loc":"Pearl Harbor, Hawaii","lat":21.34,"lon":-157.96},
    "uss_newhampshire":{"loc":"Groton, Connecticut","lat":41.38,"lon":-72.10},
    "uss_newmexico":{"loc":"Naval Station Norfolk, Virginia","lat":36.83,"lon":-76.31},
    "uss_missouri": {"loc":"Apra Harbor, Guam","lat":13.47,"lon":144.67},
    "uss_california":{"loc":"Pearl Harbor, Hawaii","lat":21.34,"lon":-157.97},
    "uss_mississippi":{"loc":"Naval Station Norfolk, Virginia","lat":36.85,"lon":-76.27},
    "uss_johnwarner":{"loc":"Naval Station Norfolk, Virginia","lat":36.82,"lon":-76.32},
    "uss_illinois": {"loc":"Apra Harbor, Guam","lat":13.46,"lon":144.65},
    "uss_washington":{"loc":"Groton, Connecticut","lat":41.35,"lon":-72.08},
    "uss_colorado": {"loc":"Pearl Harbor, Hawaii","lat":21.36,"lon":-157.95},
    "uss_indiana":  {"loc":"Naval Station Norfolk, Virginia","lat":36.84,"lon":-76.29},
    "uss_southdakota":{"loc":"Groton, Connecticut","lat":41.34,"lon":-72.09},
    "uss_vermont":  {"loc":"Naval Station Norfolk, Virginia","lat":36.83,"lon":-76.30},
    "uss_oregon":   {"loc":"Apra Harbor, Guam","lat":13.45,"lon":144.66},
    "uss_montana":  {"loc":"Groton, Connecticut","lat":41.37,"lon":-72.07},
    "uss_rickover": {"loc":"Naval Station Norfolk, Virginia","lat":36.84,"lon":-76.31},
    "uss_newjersey":{"loc":"Pearl Harbor, Hawaii","lat":21.35,"lon":-157.97},
    # USA LA-class additional
    "uss_sanfrancisco":{"loc":"Apra Harbor, Guam","lat":13.48,"lon":144.66},
    "uss_providence":{"loc":"Groton, Connecticut","lat":41.39,"lon":-72.11},
    "uss_pittsburgh":{"loc":"Naval Station Norfolk, Virginia","lat":36.81,"lon":-76.33},
    "uss_chicago":  {"loc":"Pearl Harbor, Hawaii","lat":21.35,"lon":-157.98},
    "uss_keywest":  {"loc":"Apra Harbor, Guam","lat":13.47,"lon":144.64},
    "uss_oklahomacity":{"loc":"Naval Station Norfolk, Virginia","lat":36.87,"lon":-76.28},
    "uss_louisville":{"loc":"Pearl Harbor, Hawaii","lat":21.34,"lon":-157.95},
    "uss_helena":   {"loc":"Groton, Connecticut","lat":41.36,"lon":-72.09},
    "uss_newportnews":{"loc":"Naval Station Norfolk, Virginia","lat":36.82,"lon":-76.29},
    "uss_sanjuan":  {"loc":"Groton, Connecticut","lat":41.38,"lon":-72.10},
    "uss_pasadena": {"loc":"Pearl Harbor, Hawaii","lat":21.35,"lon":-157.96},
    "uss_albany":   {"loc":"Naval Station Norfolk, Virginia","lat":36.84,"lon":-76.32},
    "uss_topeka":   {"loc":"Apra Harbor, Guam","lat":13.46,"lon":144.67},
    "uss_scranton": {"loc":"Naval Station Norfolk, Virginia","lat":36.86,"lon":-76.30},
    "uss_alexandria":{"loc":"Groton, Connecticut","lat":41.37,"lon":-72.08},
    "uss_hartford": {"loc":"Naval Station Norfolk, Virginia","lat":36.81,"lon":-76.31},
    "uss_tucson":   {"loc":"Pearl Harbor, Hawaii","lat":21.36,"lon":-157.94},
    "uss_greeneville":{"loc":"Pearl Harbor, Hawaii","lat":21.34,"lon":-157.97},
    "uss_cheyenne": {"loc":"Apra Harbor, Guam","lat":13.47,"lon":144.65},
    # Russia Borei-A additional
    "rus_olegoleg": {"loc":"Vilyuchinsk, Pacific","lat":52.96,"lon":158.72},
    "rus_suvorov":  {"loc":"Vilyuchinsk, Pacific","lat":52.93,"lon":158.68},
    "rus_emperor":  {"loc":"Barents Sea, Gadzhievo","lat":69.08,"lon":33.22},
    # Russia Delta IV additional
    "rus_verkho":   {"loc":"Barents Sea, Gadzhievo","lat":69.52,"lon":32.95},
    "rus_ekater":   {"loc":"Barents Sea, Gadzhievo","lat":69.55,"lon":33.05},
    "rus_bryansk":  {"loc":"Barents Sea, Gadzhievo","lat":69.50,"lon":32.88},
    "rus_novomoss": {"loc":"Barents Sea, Gadzhievo","lat":69.47,"lon":33.10},
    # Russia Yasen-M additional
    "rus_novosibirsk":{"loc":"Vilyuchinsk, Pacific","lat":52.92,"lon":158.65},
    # Russia Oscar II additional
    "rus_smolensk": {"loc":"Barents Sea, Severomorsk","lat":68.95,"lon":33.08},
    "rus_tomsk":    {"loc":"Rybachiy, Pacific Fleet","lat":52.91,"lon":158.63},
    # Russia Akula additional
    "rus_leopard":  {"loc":"Barents Sea, Severomorsk","lat":69.02,"lon":33.35},
    "rus_pantera":  {"loc":"Barents Sea, Severomorsk","lat":69.00,"lon":33.30},
    "rus_gepard":   {"loc":"Barents Sea, Severomorsk","lat":69.04,"lon":33.40},
    # Russia Improved Kilo additional
    "rus_krasnodar":{"loc":"Vladivostok, Pacific Fleet","lat":42.10,"lon":131.88},
    "rus_staryosk": {"loc":"Black Sea","lat":44.60,"lon":33.55},
    "rus_veliky":   {"loc":"Black Sea","lat":44.58,"lon":33.50},
    "rus_kolpino":  {"loc":"Black Sea","lat":44.63,"lon":33.48},
    "rus_ufa":      {"loc":"Vladivostok, Pacific Fleet","lat":42.10,"lon":131.88},
    "rus_mozhaisk": {"loc":"Vladivostok, Pacific Fleet","lat":42.12,"lon":131.90},
    # China additional
    "chn_jin3":     {"loc":"Yulin Base, Hainan","lat":18.23,"lon":109.53},
    "chn_jin4":     {"loc":"Yulin Base, Hainan","lat":18.21,"lon":109.49},
    "chn_shang3":   {"loc":"South China Sea","lat":18.26,"lon":109.55},
    "chn_shang4":   {"loc":"South China Sea","lat":22.32,"lon":113.96},
    "chn_yuan3":    {"loc":"South China Sea","lat":22.25,"lon":113.90},
    "chn_yuan4":    {"loc":"East China Sea","lat":25.12,"lon":121.72},
    "chn_yuan5":    {"loc":"Yulin Base, Hainan","lat":18.28,"lon":109.57},
    "chn_yuan6":    {"loc":"South China Sea","lat":20.12,"lon":110.22},
    "chn_song2":    {"loc":"East China Sea","lat":25.08,"lon":121.68},
    # UK additional
    "gbr_artful":   {"loc":"HMNB Clyde, Faslane","lat":56.06,"lon":-4.80},
    "gbr_anson":    {"loc":"HMNB Clyde, Faslane","lat":56.04,"lon":-4.76},
    "gbr_agamemnon":{"loc":"HMNB Clyde, Faslane","lat":56.07,"lon":-4.82},
    "gbr_vengeance":{"loc":"HMNB Clyde, Faslane","lat":55.97,"lon":-4.83},
    # France additional
    "fra_tourville":{"loc":"Naval Base Toulon","lat":43.10,"lon":5.93},
    "fra_degrasse": {"loc":"Naval Base Toulon","lat":43.16,"lon":5.97},
    # India Kalvari
    "ind_kalvari":  {"loc":"Arabian Sea, Karwar","lat":15.42,"lon":73.80},
    "ind_khanderi": {"loc":"Arabian Sea, Mumbai","lat":18.90,"lon":72.80},
    "ind_karanj":   {"loc":"Arabian Sea, Mumbai","lat":18.92,"lon":72.84},
    "ind_vela":     {"loc":"Arabian Sea, Karwar","lat":15.45,"lon":73.82},
    "ind_vagir":    {"loc":"Arabian Sea, Mumbai","lat":18.93,"lon":72.82},
    "ind_vagsheer": {"loc":"Arabian Sea, Karwar","lat":15.40,"lon":73.78},
    "ind_sindhu2":  {"loc":"Arabian Sea, Karwar","lat":14.80,"lon":74.10},
    "ind_sindhu3":  {"loc":"Arabian Sea, Mumbai","lat":18.88,"lon":72.78},
    "ind_shishu":   {"loc":"Arabian Sea, Mumbai","lat":18.95,"lon":72.86},
    "ind_shankush": {"loc":"Arabian Sea, Karwar","lat":14.82,"lon":74.12},
    # South Korea additional
    "kor_ahn2":     {"loc":"Sea of Japan, Jinhae","lat":35.02,"lon":129.02},
    "kor_209_1":    {"loc":"Sea of Japan, Jinhae","lat":34.82,"lon":128.98},
    "kor_209_2":    {"loc":"Sea of Japan, Jinhae","lat":34.85,"lon":129.04},
    "kor_209_3":    {"loc":"Sea of Japan, Jinhae","lat":34.80,"lon":128.94},
    "kor_209_4":    {"loc":"Sea of Japan, Jinhae","lat":35.04,"lon":129.06},
    "kor_209_5":    {"loc":"Sea of Japan, Jinhae","lat":34.78,"lon":128.96},
    "kor_cb1":      {"loc":"Sea of Japan, Jinhae","lat":35.06,"lon":129.08},
    "kor_cb2":      {"loc":"Sea of Japan, Jinhae","lat":35.00,"lon":129.00},
    # Japan Soryu additional
    "jpn_soryu2":   {"loc":"Pacific, Kure","lat":34.23,"lon":132.52},
    "jpn_soryu3":   {"loc":"Pacific, Yokosuka","lat":35.47,"lon":139.65},
    "jpn_soryu4":   {"loc":"Pacific, Kure","lat":34.20,"lon":132.48},
    "jpn_soryu5":   {"loc":"Pacific, Yokosuka","lat":35.44,"lon":139.62},
    "jpn_soryu6":   {"loc":"Pacific, Kure","lat":34.18,"lon":132.45},
    "jpn_soryu7":   {"loc":"Pacific, Yokosuka","lat":35.49,"lon":139.67},
    "jpn_soryu8":   {"loc":"Pacific, Kure","lat":34.22,"lon":132.50},
    "jpn_soryu9":   {"loc":"Pacific, Yokosuka","lat":35.43,"lon":139.60},
    "jpn_soryu10":  {"loc":"Pacific, Kure","lat":34.25,"lon":132.55},
    "jpn_taigei2":  {"loc":"Pacific, Yokosuka","lat":35.42,"lon":139.58},
    "jpn_oyashio2": {"loc":"Pacific, Kure","lat":34.19,"lon":132.46},
    "jpn_oyashio3": {"loc":"Pacific, Yokosuka","lat":35.45,"lon":139.63},
    # Germany additional
    "deu_u31":      {"loc":"Baltic Sea, Kiel","lat":54.33,"lon":10.17},
    "deu_u33":      {"loc":"Baltic Sea, Kiel","lat":54.30,"lon":10.13},
    "deu_u35":      {"loc":"Baltic Sea, Kiel","lat":54.35,"lon":10.15},
    "deu_u36":      {"loc":"Baltic Sea, Kiel","lat":54.28,"lon":10.11},
    # Italy additional
    "ita_scire":    {"loc":"Tyrrhenian Sea, Naples","lat":40.83,"lon":14.28},
    "ita_longobardo":{"loc":"Ionian Sea, Augusta","lat":37.18,"lon":15.22},
    "ita_pelosi":   {"loc":"Ionian Sea, Augusta","lat":37.20,"lon":15.24},
    "ita_prini":    {"loc":"Ionian Sea, Augusta","lat":37.02,"lon":15.50},
    # Australia additional
    "aus_waller":   {"loc":"HMAS Stirling, Perth","lat":-31.86,"lon":115.96},
    "aus_dechaineux":{"loc":"HMAS Stirling, Perth","lat":-31.88,"lon":115.98},
    "aus_sheean":   {"loc":"HMAS Stirling, Perth","lat":-31.84,"lon":115.92},
    "aus_rankin":   {"loc":"HMAS Stirling, Perth","lat":-31.90,"lon":116.00},
    # Greece additional
    "grc_pipinos":  {"loc":"Aegean Sea, Salamis","lat":37.93,"lon":23.45},
    "grc_proteus":  {"loc":"Aegean Sea, Salamis","lat":37.96,"lon":23.50},
    "grc_nereus":   {"loc":"Aegean Sea, Salamis","lat":37.91,"lon":23.43},
    "grc_triton":   {"loc":"Aegean Sea, Salamis","lat":37.89,"lon":23.47},
    "grc_okeanos":  {"loc":"Aegean Sea, Salamis","lat":37.94,"lon":23.49},
    # Turkey additional
    "tur_18mart":   {"loc":"Golcuk, Sea of Marmara","lat":40.74,"lon":29.94},
    "tur_atilay":   {"loc":"Golcuk, Sea of Marmara","lat":40.75,"lon":29.96},
    "tur_saldiray": {"loc":"Golcuk, Sea of Marmara","lat":40.71,"lon":29.90},
    "tur_muratreis":{"loc":"Golcuk, Sea of Marmara","lat":40.70,"lon":29.88},
    "tur_yildiray": {"loc":"Golcuk, Sea of Marmara","lat":40.73,"lon":29.92},
    # Netherlands additional
    "nld_zeeleeuw": {"loc":"Den Helder, Netherlands","lat":52.98,"lon":4.78},
    # Norway additional
    "nor_ula":      {"loc":"North Sea, Bergen","lat":60.38,"lon":5.30},
    "nor_utstein":  {"loc":"North Sea, Bergen","lat":60.40,"lon":5.33},
    "nor_uthaug":   {"loc":"North Sea, Bergen","lat":60.41,"lon":5.34},
    "nor_uredd":    {"loc":"North Sea, Bergen","lat":60.44,"lon":5.37},
    # Sweden additional
    "swe_uppland":  {"loc":"Baltic Sea, Stockholm","lat":59.35,"lon":18.08},
    "swe_halland":  {"loc":"Baltic Sea, Karlskrona","lat":55.60,"lon":14.10},
    "swe_ostergot": {"loc":"Baltic Sea, Stockholm","lat":59.02,"lon":18.52},
    # Brazil additional
    "bra_humaitá":  {"loc":"Guanabara Bay, Rio de Janeiro","lat":-22.90,"lon":-43.14},
    "bra_tonelero": {"loc":"Guanabara Bay, Rio de Janeiro","lat":-22.86,"lon":-43.10},
    "bra_angostura":{"loc":"Guanabara Bay, Rio de Janeiro","lat":-22.84,"lon":-43.08},
    "bra_tupi":     {"loc":"Guanabara Bay, Rio de Janeiro","lat":-22.92,"lon":-43.16},
    "bra_tamoio":   {"loc":"Guanabara Bay, Rio de Janeiro","lat":-22.94,"lon":-43.18},
    # Chile additional
    "chl_thompson": {"loc":"Talcahuano, Chile","lat":-36.52,"lon":-74.02},
    "chl_simpson":  {"loc":"Talcahuano, Chile","lat":-36.55,"lon":-74.05},
    # Peru additional
    "per_islay":    {"loc":"South Pacific, Callao","lat":-11.52,"lon":-78.52},
    "per_arica":    {"loc":"South Pacific, Callao","lat":-11.55,"lon":-78.55},
    "per_chipana":  {"loc":"South Pacific, Callao","lat":-11.48,"lon":-78.48},
    # Colombia additional
    "col_pijao":    {"loc":"Caribbean Sea, Cartagena","lat":11.02,"lon":-76.52},
    # Venezuela additional
    "ven_caribe":   {"loc":"Caribbean Sea, Puerto Cabello","lat":11.52,"lon":-67.52},
    # Argentina additional
    "arg_salta":    {"loc":"South Atlantic, Mar del Plata","lat":-38.52,"lon":-58.52},
    # Ecuador (new)
    "ecu_shyri":    {"loc":"Pacific, Guayaquil","lat":-2.20,"lon":-80.92},
    "ecu_huanca":   {"loc":"Pacific, Guayaquil","lat":-2.22,"lon":-80.94},
    # Portugal additional
    "prt_arpao":    {"loc":"Atlantic, Setubal","lat":38.50,"lon":-8.90},
    # Canada additional
    "can_chicoutimi":{"loc":"CFB Esquimalt, British Columbia","lat":49.32,"lon":-123.07},
    # Israel additional
    "isr_dolphin":  {"loc":"Eastern Mediterranean, Haifa","lat":32.82,"lon":34.52},
    "isr_tekuma":   {"loc":"Red Sea, Eilat","lat":29.52,"lon":34.90},
    "isr_rahav":    {"loc":"Eastern Mediterranean, Haifa","lat":32.84,"lon":34.54},
    # Singapore additional
    "sgp_centurion":{"loc":"Strait of Malacca, Singapore","lat":1.26,"lon":103.76},
    "sgp_conqueror":{"loc":"Strait of Malacca, Singapore","lat":1.24,"lon":103.74},
    # Malaysia additional
    "mys_razak2":   {"loc":"South China Sea, Kota Kinabalu","lat":5.02,"lon":118.02},
    # Vietnam additional
    "vnm_hcmc":     {"loc":"Cam Ranh Bay, Vietnam","lat":11.95,"lon":109.21},
    "vnm_haiphong": {"loc":"Cam Ranh Bay, Vietnam","lat":11.97,"lon":109.23},
    "vnm_danang":   {"loc":"Cam Ranh Bay, Vietnam","lat":11.92,"lon":109.18},
    "vnm_khanh":    {"loc":"Cam Ranh Bay, Vietnam","lat":11.90,"lon":109.16},
    "vnm_baria":    {"loc":"Cam Ranh Bay, Vietnam","lat":11.88,"lon":109.14},
    # Indonesia (new)
    "idn_nagapasa": {"loc":"Java Sea, Jakarta","lat":-6.10,"lon":106.88},
    "idn_ardadedali":{"loc":"Java Sea, Jakarta","lat":-6.12,"lon":106.90},
    "idn_alugoro":  {"loc":"Java Sea, Surabaya","lat":-7.20,"lon":112.73},
    # Pakistan additional
    "pak_khalid":   {"loc":"Arabian Sea, Karachi","lat":24.84,"lon":66.99},
    "pak_saad":     {"loc":"Arabian Sea, Karachi","lat":24.80,"lon":66.95},
    # Iran additional
    "irn_tareg":    {"loc":"Strait of Hormuz, Bandar Abbas","lat":27.20,"lon":56.30},
    "irn_noor":     {"loc":"Strait of Hormuz, Bandar Abbas","lat":27.22,"lon":56.32},
    "irn_yunes":    {"loc":"Strait of Hormuz, Bandar Abbas","lat":27.18,"lon":56.28},
    "irn_besat":    {"loc":"Strait of Hormuz","lat":27.24,"lon":56.34},
    "irn_ghadir1":  {"loc":"Persian Gulf","lat":26.55,"lon":53.92},
    "irn_ghadir2":  {"loc":"Persian Gulf","lat":26.57,"lon":53.94},
    # DPRK additional
    "prk_romeo1":   {"loc":"Sea of Japan, Sinpo","lat":40.05,"lon":128.44},
    "prk_romeo2":   {"loc":"Sea of Japan, Sinpo","lat":40.08,"lon":128.46},
    "prk_sango1":   {"loc":"Sea of Japan","lat":39.80,"lon":128.40},
    "prk_sango2":   {"loc":"Sea of Japan","lat":39.82,"lon":128.42},
    # Taiwan additional
    "twn_hailung2": {"loc":"Pacific, Zuoying","lat":23.52,"lon":122.02},
    # Egypt additional
    "egy_s41":      {"loc":"Eastern Mediterranean, Alexandria","lat":32.02,"lon":29.02},
    "egy_s42":      {"loc":"Eastern Mediterranean, Alexandria","lat":31.98,"lon":28.98},
    "egy_s43":      {"loc":"Eastern Mediterranean, Alexandria","lat":32.04,"lon":29.04},
    # Algeria additional
    "dza_kellich":  {"loc":"Western Mediterranean, Algiers","lat":36.75,"lon":3.19},
    "dza_korfou":   {"loc":"Western Mediterranean, Algiers","lat":36.71,"lon":3.15},
    "dza_slimane":  {"loc":"Western Mediterranean, Algiers","lat":36.69,"lon":3.13},
    # Poland (new)
    "pol_orzel":    {"loc":"Baltic Sea, Gdynia","lat":54.53,"lon":18.55},
}

SUB_NAME_MAP = {
    # USA Ohio SSBNs / SSGNs
    "uss ohio":"uss_ohio","ssbn-726":"uss_ohio",
    "uss michigan":"uss_mich","ssgn-727":"uss_mich",
    "uss florida":"uss_florida","ssgn-728":"uss_florida",
    "uss georgia":"uss_georgia","ssgn-729":"uss_georgia",
    "henry m. jackson":"uss_jackson","ssbn-730":"uss_jackson",
    "uss alabama":"uss_alabama","ssbn-731":"uss_alabama",
    "uss alaska":"uss_alaska","ssbn-732":"uss_alaska",
    "uss nevada":"uss_nevada","ssbn-733":"uss_nevada",
    "uss tennessee":"uss_tenn","ssbn-734":"uss_tenn",
    "uss pennsylvania":"uss_pennsylvania","ssbn-735":"uss_pennsylvania",
    "uss west virginia":"uss_westva","ssbn-736":"uss_westva",
    "uss kentucky":"uss_kentucky","ssbn-737":"uss_kentucky",
    "uss maryland":"uss_maryland","ssbn-738":"uss_maryland",
    "uss nebraska":"uss_nebraska","ssbn-739":"uss_nebraska",
    "uss rhode island":"uss_rhodeisland","ssbn-740":"uss_rhodeisland",
    "uss maine":"uss_maine","ssbn-741":"uss_maine",
    "uss wyoming":"uss_wyoming","ssbn-742":"uss_wyoming",
    "uss louisiana":"uss_louisiana","ssbn-743":"uss_louisiana",
    # USA Seawolf
    "uss seawolf":"uss_seawolf","ssn-21":"uss_seawolf",
    "uss connecticut":"uss_connecticut","ssn-22":"uss_connecticut",
    "uss jimmy carter":"uss_jcarter","ssn-23":"uss_jcarter",
    # USA Virginia-class
    "uss virginia":"uss_virginia","ssn-774":"uss_virginia",
    "uss texas":"uss_texas","ssn-775":"uss_texas",
    "uss hawaii":"uss_hawaii","ssn-776":"uss_hawaii",
    "uss north carolina":"uss_northcarolina","ssn-777":"uss_northcarolina",
    "uss new hampshire":"uss_newhampshire","ssn-778":"uss_newhampshire",
    "uss new mexico":"uss_newmexico","ssn-779":"uss_newmexico",
    "uss missouri":"uss_missouri","ssn-780":"uss_missouri",
    "uss california":"uss_california","ssn-781":"uss_california",
    "uss mississippi":"uss_mississippi","ssn-782":"uss_mississippi",
    "uss minnesota":"uss_minnesota","ssn-783":"uss_minnesota",
    "uss north dakota":"uss_ndakota","ssn-784":"uss_ndakota",
    "uss john warner":"uss_johnwarner","ssn-785":"uss_johnwarner",
    "uss illinois":"uss_illinois","ssn-786":"uss_illinois",
    "uss washington":"uss_washington","ssn-787":"uss_washington",
    "uss colorado":"uss_colorado","ssn-788":"uss_colorado",
    "uss indiana":"uss_indiana","ssn-789":"uss_indiana",
    "uss south dakota":"uss_southdakota","ssn-790":"uss_southdakota",
    "uss delaware":"uss_delaware","ssn-791":"uss_delaware",
    "uss vermont":"uss_vermont","ssn-792":"uss_vermont",
    "uss oregon":"uss_oregon","ssn-793":"uss_oregon",
    "uss montana":"uss_montana","ssn-794":"uss_montana",
    "uss rickover":"uss_rickover","hyman g. rickover":"uss_rickover","ssn-795":"uss_rickover",
    "uss new jersey":"uss_newjersey","ssn-796":"uss_newjersey",
    # USA LA-class
    "uss san francisco":"uss_sanfrancisco","ssn-711":"uss_sanfrancisco",
    "uss springfield":"uss_springfield","ssn-761":"uss_springfield",
    "uss providence":"uss_providence","ssn-719":"uss_providence",
    "uss pittsburgh":"uss_pittsburgh","ssn-720":"uss_pittsburgh",
    "uss chicago":"uss_chicago","ssn-721":"uss_chicago",
    "uss key west":"uss_keywest","ssn-722":"uss_keywest",
    "uss oklahoma city":"uss_oklahomacity","ssn-723":"uss_oklahomacity",
    "uss louisville":"uss_louisville","ssn-724":"uss_louisville",
    "uss helena":"uss_helena","ssn-725":"uss_helena",
    "uss newport news":"uss_newportnews","ssn-750":"uss_newportnews",
    "uss san juan":"uss_sanjuan","ssn-751":"uss_sanjuan",
    "uss pasadena":"uss_pasadena","ssn-752":"uss_pasadena",
    "uss albany":"uss_albany","ssn-753":"uss_albany",
    "uss topeka":"uss_topeka","ssn-754":"uss_topeka",
    "uss scranton":"uss_scranton","ssn-756":"uss_scranton",
    "uss alexandria":"uss_alexandria","ssn-757":"uss_alexandria",
    "uss hartford":"uss_hartford","ssn-768":"uss_hartford",
    "uss tucson":"uss_tucson","ssn-770":"uss_tucson",
    "uss greeneville":"uss_greeneville","ssn-772":"uss_greeneville",
    "uss cheyenne":"uss_cheyenne","ssn-773":"uss_cheyenne",
    # Russia
    "yuri dolgoruky":"rus_yuri","k-535":"rus_yuri",
    "vladimir monomakh":"rus_vlad","k-551":"rus_vlad",
    "petropavlovsk":"rus_vlad",
    "alexandre nevski":"rus_nevsky","k-550":"rus_nevsky",
    "knyaz vladimir":"rus_knyaz","k-549":"rus_knyaz",
    "knyaz oleg":"rus_olegoleg","k-552":"rus_olegoleg",
    "generalissimus suvorov":"rus_suvorov","k-553":"rus_suvorov",
    "imperator alexander":"rus_emperor","k-554":"rus_emperor",
    "severodvinsk":"rus_sev","k-329 sev":"rus_sev",
    "kazan":"rus_kazan","k-561":"rus_kazan",
    "novosibirsk":"rus_novosibirsk","k-573":"rus_novosibirsk",
    "krasnoyarsk":"rus_krasno",
    "belgorod":"rus_belg",
    "novorossiysk":"rus_kilo","b-261":"rus_kilo",
    "rostov":"rus_rostov","b-237":"rus_rostov",
    "krasnodar":"rus_krasnodar","b-265":"rus_krasnodar",
    "stary oskol":"rus_staryosk","b-262":"rus_staryosk",
    "veliky novgorod":"rus_veliky","b-268":"rus_veliky",
    "kolpino":"rus_kolpino","b-271":"rus_kolpino",
    "orel":"rus_orel","k-266":"rus_orel",
    "smolensk":"rus_smolensk","k-410":"rus_smolensk",
    "tomsk":"rus_tomsk","k-150":"rus_tomsk",
    "tver":"rus_tver","k-456":"rus_tver",
    "verkhoturye":"rus_verkho","k-84":"rus_verkho",
    "toula":"rus_tula","k-114":"rus_tula",
    "karelia":"rus_karelia","k-18":"rus_karelia",
    "bryansk":"rus_bryansk","k-117":"rus_bryansk",
    "novomoskovsk":"rus_novomoss","k-407":"rus_novomoss",
    "leopard":"rus_leopard","k-328":"rus_leopard",
    "pantera":"rus_pantera","k-317":"rus_pantera",
    "gepard":"rus_gepard","k-335":"rus_gepard",
    # China
    "long march 17":"chn_jin","jin class":"chn_jin","type 094":"chn_jin",
    "long march 6":"chn_jin2","long march 7":"chn_jin3","long march 8":"chn_jin4",
    "long march 11":"chn_shang","shang class":"chn_shang","type 093":"chn_shang",
    "long march 16":"chn_shang2","long march 20":"chn_shang3","long march 21":"chn_shang4",
    "yuan class":"chn_yuan1","type 039a":"chn_yuan1","type 039b":"chn_yuan2","type 039c":"chn_yuan5",
    "song class":"chn_song","type 039":"chn_song",
    # UK
    "hms vanguard":"gbr_vanguard","s28":"gbr_vanguard","vanguard class":"gbr_vanguard",
    "hms victorious":"gbr_victorious","s29":"gbr_victorious",
    "hms vigilant":"gbr_vigilant","s30":"gbr_vigilant",
    "hms vengeance":"gbr_vengeance","s31":"gbr_vengeance",
    "hms astute":"gbr_astute","s119":"gbr_astute","astute class":"gbr_astute",
    "hms ambush":"gbr_ambush","s120":"gbr_ambush",
    "hms audacious":"gbr_audacious","s122":"gbr_audacious",
    "hms artful":"gbr_artful","s121":"gbr_artful",
    "hms anson":"gbr_anson","s123":"gbr_anson",
    "hms agamemnon":"gbr_agamemnon","s124":"gbr_agamemnon",
    # France
    "le triomphant":"fra_triomphant","s616":"fra_triomphant","triomphant":"fra_triomphant",
    "le terrible":"fra_terrible","s619":"fra_terrible",
    "le vigilant":"fra_vigilant","s618":"fra_vigilant",
    "le temeraire":"fra_temeraire","s617":"fra_temeraire",
    "suffren":"fra_suffren","q285":"fra_suffren",
    "duguay-trouin":"fra_duguay","q286":"fra_duguay",
    "tourville":"fra_tourville","q287":"fra_tourville",
    "de grasse":"fra_degrasse","q288":"fra_degrasse",
    "barracuda class":"fra_suffren",
    # India
    "ins arihant":"ind_arihant","s2":"ind_arihant","arihant":"ind_arihant",
    "ins aridhaman":"ind_aridhaman","s3":"ind_aridhaman",
    "ins chakra":"ind_chakra",
    "ins kalvari":"ind_kalvari","s50":"ind_kalvari","kalvari class":"ind_kalvari",
    "ins khanderi":"ind_khanderi","s51":"ind_khanderi",
    "ins karanj":"ind_karanj","s52":"ind_karanj",
    "ins vela":"ind_vela","s53":"ind_vela",
    "ins vagir":"ind_vagir","s54":"ind_vagir",
    "ins vagsheer":"ind_vagsheer","s55":"ind_vagsheer",
    "ins sindhughost":"ind_sindhughost","ins sindhuvir":"ind_sindhu2","ins sindhushastra":"ind_sindhu3",
    "ins shishumar":"ind_shishu","ins shankush":"ind_shankush",
    # Germany
    "u-31":"deu_u31","u-32":"deu_u32","u-33":"deu_u33","u-34":"deu_u34",
    "u-35":"deu_u35","u-36":"deu_u36","type 212":"deu_u32",
    # Japan
    "js oyashio":"jpn_oyashio","js michishio":"jpn_oyashio2","js uzushio":"jpn_oyashio3",
    "js soryu":"jpn_soryu","js unryu":"jpn_soryu2","js hakuryu":"jpn_soryu3",
    "js kenryu":"jpn_soryu4","js zuiryu":"jpn_soryu5","js kokuryu":"jpn_soryu6",
    "js jinryu":"jpn_soryu7","js sekiryu":"jpn_soryu8","js seiryu":"jpn_soryu9",
    "js shoryu":"jpn_soryu10","soryu class":"jpn_soryu",
    "js taigei":"jpn_taigei","ss-513":"jpn_taigei","js hakugei":"jpn_taigei2","taigei class":"jpn_taigei",
    # South Korea
    "dosan ahn":"kor_dosan","kss-iii":"kor_dosan","ssn-3000":"kor_dosan",
    "roks yi sunsin":"kor_yisunshin","son won-il":"kor_sonwonil",
    "roks ahn jung":"kor_209_1","roks kim jwa":"kor_209_2","roks yun bong":"kor_209_3",
    "roks hong beom":"kor_209_5","roks yu gwan":"kor_209_4",
    "chang bogo":"kor_cb1","ss-061":"kor_cb1",
    # North Korea
    "hero kim":"prk_hero","kim kun ok":"prk_hero","sinpo":"prk_hero",
    "romeo class":"prk_romeo1","sang-o":"prk_sango1","sang o class":"prk_sango1",
    # Iran
    "iris fateh":"irn_fateh","iris besat":"irn_besat","fateh class":"irn_fateh",
    "iris tareq":"irn_tareg","iris noor":"irn_noor","iris yunes":"irn_yunes",
    "ghadir":"irn_ghadir1","ghadir class":"irn_ghadir1",
    # Turkey
    "tcg preveze":"tur_preveze","tcg sakarya":"tur_sakarya","tcg pirireis":"tur_pirireis",
    "tcg 18 mart":"tur_18mart","tcg murat reis":"tur_muratreis",
    "type 209":"tur_preveze","preveze class":"tur_preveze","reis class":"tur_pirireis",
    # Australia
    "hmas collins":"aus_collins","hmas farncomb":"aus_farncomb","hmas waller":"aus_waller",
    "hmas dechaineux":"aus_dechaineux","hmas sheean":"aus_sheean","hmas rankin":"aus_rankin",
    "collins class":"aus_collins",
    # Norway
    "hnoMs utsira":"nor_utsira","hnoMs utvaer":"nor_utvaer",
    "hnoMs ula":"nor_ula","hnoMs utstein":"nor_utstein","hnoMs uthaug":"nor_uthaug","hnoMs uredd":"nor_uredd",
    "ula class":"nor_ula",
    # Sweden
    "gotland":"swe_gotland","hswms gotland":"swe_gotland","hswms halland":"swe_halland",
    "hswms sodermanland":"swe_sodermanland","hswms ostergotland":"swe_ostergot",
    "hswms uppland":"swe_uppland","a26":"swe_uppland","blekinge class":"swe_uppland",
    # Netherlands
    "hnlms walrus":"nld_walrus","hnlms bruinvis":"nld_bruinvis","hnlms zeeleeuw":"nld_zeeleeuw",
    "walrus class":"nld_walrus",
    # Canada
    "hmcs cornerbrook":"can_cornerbrook","hmcs windsor":"can_windsor","hmcs chicoutimi":"can_chicoutimi",
    "victoria class":"can_cornerbrook",
    # Greece
    "hs papanikolis":"grc_papa","hs matrozos":"grc_matrozos","hs pipinos":"grc_pipinos",
    "hs proteus":"grc_proteus","hs nereus":"grc_nereus","hs triton":"grc_triton","hs okeanos":"grc_okeanos",
    "type 214":"grc_papa",
    # Italy
    "its todaro":"ita_todaro","its scire":"ita_scire","its longobardo":"ita_longobardo",
    "its pelosi":"ita_pelosi","its prini":"ita_prini","type 212a":"ita_todaro",
    # Spain
    "isaac peral":"esp_isaac","s-80":"esp_isaac","s80":"esp_isaac",
    # Brazil
    "riachuelo":"bra_riachuelo","humaita":"bra_humaitá","tonelero":"bra_tonelero",
    "angostura":"bra_angostura","tupi":"bra_tupi","tamoio":"bra_tamoio",
    # Chile
    "cs carrera":"chl_carrera","cs ohiggins":"chl_ohiggins","cs thompson":"chl_thompson","cs simpson":"chl_simpson",
    "scorpene":"bra_riachuelo",
    # Vietnam
    "hq-182":"vnm_hanoi","ha noi":"vnm_hanoi","ho chi minh":"vnm_hcmc","hq-184":"vnm_hcmc",
    "hai phong":"vnm_haiphong","hq-186":"vnm_haiphong","da nang":"vnm_danang","hq-187":"vnm_danang",
    "khanh hoa":"vnm_khanh","ba ria":"vnm_baria",
    # Vietnam fleet generic
    "kilo class vietnam":"vnm_hanoi",
    # Indonesia
    "kri nagapasa":"idn_nagapasa","kri ardadedali":"idn_ardadedali","kri alugoro":"idn_alugoro",
    # Pakistan
    "pns hamza":"pak_hamza","pns khalid":"pak_khalid","pns saad":"pak_saad","agosta":"pak_hamza",
    # Israel
    "ins dolphin":"isr_dolphin","ins tekuma":"isr_tekuma","ins leviatan":"isr_leviathan",
    "ins tanin":"isr_tanin","ins rahav":"isr_rahav","dolphin class":"isr_dolphin",
    # Singapore
    "rss impeccable":"sgp_impeccable","rss stalwart":"sgp_stalwart",
    "rss centurion":"sgp_centurion","rss conqueror":"sgp_conqueror","type 218":"sgp_centurion",
    # Malaysia
    "kd tun razak":"mys_razak","kd tun abdul razak":"mys_razak",
    # Algeria
    "rais hadj":"dza_rais","rais kellich":"dza_kellich","rais korfou":"dza_korfou","el hadj slimane":"dza_slimane",
    # Egypt
    "ens s41":"egy_s41","ens s42":"egy_s42","ens s43":"egy_s43","ens s44":"egy_s44",
    # Taiwan
    "rocs hai lung":"twn_hailung","rocs hai kun":"twn_haikun","rocs hai hu":"twn_hailung2",
    # Ecuador
    "bae shyri":"ecu_shyri","bae huancavilca":"ecu_huanca",
    # Poland
    "orp orzel":"pol_orzel","orzel":"pol_orzel",
    # Portugal
    "nrp tridente":"prt_tridente","nrp arpao":"prt_arpao",
    # Peru
    "bap pisagua":"per_pisagua","bap islay":"per_islay","bap arica":"per_arica","bap chipana":"per_chipana",
    # Colombia
    "arc tayrona":"col_tayrona","arc pijao":"col_pijao",
    # Argentina
    "ara santa cruz":"arg_santacruz","ara salta":"arg_salta",
    # Venezuela
    "arv sabalo":"ven_sabalo","arv caribe":"ven_caribe",
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

def _make_sighting(title, text, link, pub, source_name, priority):
    """Build a sighting dict from raw text fields."""
    sub_id, sub_name = extract_sub_id(title + ' ' + text)
    loc = extract_sea_location(title + ' ' + text)
    if loc:
        loc_name, (lat, lon) = loc
        lat += random.uniform(-0.3, 0.3)
        lon += random.uniform(-0.3, 0.3)
    elif sub_id and sub_id in SUB_BASELINES:
        b = SUB_BASELINES[sub_id]
        loc_name = b['loc']
        lat = b['lat'] + random.uniform(-0.2, 0.2)
        lon = b['lon'] + random.uniform(-0.2, 0.2)
    else:
        lat = lon = None
        loc_name = 'Position Unconfirmed'
    return {
        'id': link or title,
        'sub_id': sub_id, 'sub_name': sub_name,
        'title': title, 'summary': text[:600],
        'source': source_name, 'source_url': link,
        'location': loc_name.title() if loc_name else 'Position Unconfirmed',
        'lat': round(lat, 3) if lat else None,
        'lon': round(lon, 3) if lon else None,
        'published': pub,
        'scraped_at': datetime.now(timezone.utc).isoformat(),
        'priority': priority,
    }


def scrape_reddit():
    """Scrape public subreddits via JSON API (no auth needed)."""
    print(f"\n📱 Reddit...")
    headers = {'User-Agent': 'DeepStateOSINT/1.0 submarine-tracker github.com/qmfire18-source'}
    sightings = []; seen = set()
    for sub in REDDIT_SUBS:
        try:
            url = f'https://www.reddit.com/r/{sub}/new.json?limit=25'
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 429:
                print(f"   ⚠️ r/{sub}: rate limited"); time.sleep(3); continue
            if resp.status_code != 200:
                continue
            posts = resp.json().get('data', {}).get('children', [])
            count = 0
            for post in posts:
                p = post.get('data', {})
                title = p.get('title', '')
                text = p.get('selftext', '')
                link = 'https://www.reddit.com' + p.get('permalink', '')
                pub = datetime.fromtimestamp(
                    p.get('created_utc', 0), tz=timezone.utc
                ).isoformat()
                if not is_sub_article(title, text):
                    continue
                uid = link
                if uid in seen: continue
                seen.add(uid)
                sg = _make_sighting(title, text, link, pub, f'Reddit r/{sub}', 2)
                sightings.append(sg)
                count += 1
                icon = '☢' if sg['sub_id'] else '📰'
                print(f"   {icon} [{sg['sub_id'] or 'GEN'}] {title[:55]}")
            print(f"   r/{sub}: {count} articles sous-marins")
            time.sleep(1)  # politesse Reddit
        except Exception as e:
            print(f"   ✗ r/{sub}: {e}")
    return sightings


def scrape_telegram():
    """Scrape public Telegram channels via web preview (t.me/s/) — no API key needed."""
    print(f"\n📨 Telegram...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    sightings = []; seen = set()
    for channel in TELEGRAM_CHANNELS:
        try:
            url = f'https://t.me/s/{channel}'
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"   ✗ @{channel}: HTTP {resp.status_code}"); continue
            soup = BeautifulSoup(resp.text, 'lxml')
            messages = soup.find_all('div', class_='tgme_widget_message_wrap')
            count = 0
            for msg in messages:
                # Texte du message
                txt_el = msg.find('div', class_='tgme_widget_message_text')
                text = txt_el.get_text(' ') if txt_el else ''
                # Date et lien
                time_el = msg.find('time')
                pub = time_el.get('datetime', datetime.now(timezone.utc).isoformat()) if time_el else ''
                link_el = msg.find('a', class_='tgme_widget_message_date')
                link = link_el.get('href', url) if link_el else url
                if not is_sub_article(text, ''):
                    continue
                uid = link
                if uid in seen: continue
                seen.add(uid)
                sg = _make_sighting(text[:120], text, link, pub, f'Telegram @{channel}', 2)
                sightings.append(sg)
                count += 1
                icon = '☢' if sg['sub_id'] else '📰'
                print(f"   {icon} [{sg['sub_id'] or 'GEN'}] @{channel}: {text[:50]}")
            print(f"   @{channel}: {count} messages sous-marins")
            time.sleep(1)
        except Exception as e:
            print(f"   ✗ @{channel}: {e}")
    return sightings


def scrape_live():
    """Scrape live RSS feeds for fresh sightings."""
    sightings=[]; seen=set()
    print(f"\n{'='*55}")
    print(f"DEEP STATE SCRAPER v4 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
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
                lat+=random.uniform(-0.3,0.3); lon+=random.uniform(-0.3,0.3)
            elif sub_id and sub_id in SUB_BASELINES:
                b=SUB_BASELINES[sub_id]
                loc_name=b["loc"]
                lat=b["lat"]+random.uniform(-0.2,0.2)
                lon=b["lon"]+random.uniform(-0.2,0.2)
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
        lat=b["lat"]+random.uniform(-0.1,0.1)
        lon=b["lon"]+random.uniform(-0.1,0.1)
        baseline.append({
            "id":f"baseline_{sub_id}",
            "is_baseline":True,  # never overrides HTML estimated positions
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
    live = scrape_live()
    live += scrape_reddit()
    live += scrape_telegram()
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

