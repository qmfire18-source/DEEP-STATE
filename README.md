# DEEP STATE — Submarine Intelligence Map

**292 submarines · 30+ navies · Real-time OSINT · Bilingual FR/EN**

🔗 **[→ Launch the map](https://qmfire18-source.github.io/DEEP-STATE/)**

![GitHub last commit](https://img.shields.io/github/last-commit/qmfire18-source/DEEP-STATE)
![GitHub Pages](https://img.shields.io/badge/hosted-GitHub%20Pages-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Submarines](https://img.shields.io/badge/submarines-292-navy)

---

## What is it?

**Deep State** is an open-source submarine intelligence map aggregating public OSINT data from naval analysts, military news outlets and official naval communications. It covers every submarine fleet in the world — from US Ohio SSBNs to North Korean Sinpo-C boats.

Positions are classified into three tiers:

| Icon | Meaning |
|------|---------|
| 📡 | **OSINT confirmed** — sourced from a published news article or official report |
| 〜 | **Estimated patrol area** — plausible zone based on operational doctrine, not confirmed |
| 📍 | **At homeport** — baseline position from public fleet registers |

---

## Features

- **Interactive flat map** (Leaflet + Esri satellite imagery) with dashed lines connecting each deployed submarine to its home base
- **3D globe** (Three.js) with real-time submarine positions
- **Nuclear deployment level** — live bar tracking confirmed nuclear submarines away from base
- **OSINT feed** — auto-scraped every 6 hours from USNI News, Naval News, HI Sutton
- **Full submarine specs** on click — displacement, speed, crew, armament, description
- **Search & filter** by type (SSN / SSBN / SSGN / SS), nation, nuclear status
- **Fleet comparison** — top 14 submarine fleets ranked
- **Bilingual** — French / English interface toggle

---

## Submarines covered

| Navy | Count | Classes |
|------|-------|---------|
| 🇺🇸 United States | 48 | Ohio (SSBN/SSGN), Virginia, Seawolf, Los Angeles |
| 🇷🇺 Russia | 38 | Borei-A, Yasen-M, Oscar II, Delta IV, Kilo 636.3, Belgorod |
| 🇨🇳 China | 16 | Type 094A Jin, Type 093 Shang, Type 039 Yuan/Song |
| 🇯🇵 Japan | 15 | Taigei, Sōryū, Oyashio |
| 🇰🇷 South Korea | 9 | KSS-III, Type 214, Type 209 |
| 🇬🇧 United Kingdom | 7 | Vanguard, Astute |
| 🇮🇳 India | 11 | Arihant, Scorpène (Kalvari), Kilo |
| 🇫🇷 France | 7 | Triomphant, Barracuda (Suffren) |
| 🇩🇪 Germany | 6 | Type 212A |
| 🇬🇷 Greece | 7 | Type 214, Type 209 |
| 🇹🇷 Turkey | 8 | Reis (Type 214), Preveze/Ay (Type 209) |
| 🇮🇱 Israel | 5 | Dolphin II |
| + 19 more navies | 50+ | Australia, Norway, Sweden, Italy, Vietnam… |

---

## Data sources

All data is **public**. No classified information is used or implied.

- [USNI News Fleet Tracker](https://news.usni.org/category/fleet-tracker)
- [USNI News Western Pacific Pulse](https://news.usni.org/category/news/western-pacific-pulse)
- [HI Sutton — Covert Shores](https://www.hisutton.com)
- [Naval News](https://www.navalnews.com)
- [IISS Military Balance 2025](https://www.iiss.org/publications/the-military-balance/)
- [Wikipedia naval vessel articles](https://en.wikipedia.org/wiki/List_of_submarines) (specs baseline)

---

## How it works

```
GitHub Actions (every 6h)
  └─ scraper.py
       ├─ Fetches RSS feeds from USNI / Naval News / HI Sutton
       ├─ Matches article text to submarine IDs via SUB_NAME_MAP
       ├─ Writes confirmed positions → sightings.json (position_updates)
       └─ Generates homeport baselines for unmentioned submarines

Browser loads v4.html
  └─ Fetches sightings.json
       ├─ position_updates → moves sub + sets 📡 OSINT badge
       ├─ estimated positions (coded in HTML) → shows 〜 badge
       └─ homeport baseline → shows 📍 badge
```

---

## Tech stack

| Layer | Tech |
|-------|------|
| Map | [Leaflet 1.9.4](https://leafletjs.com/) + Esri World Imagery tiles |
| Globe | [Three.js r128](https://threejs.org/) + Blue Marble texture |
| Scraper | Python 3 · feedparser · BeautifulSoup4 · requests |
| CI/CD | GitHub Actions (scheduled every 6 hours) |
| Hosting | GitHub Pages (zero cost) |
| Framework | None — pure HTML/CSS/JS, zero dependencies at runtime |

---

## Run locally

```bash
git clone https://github.com/qmfire18-source/DEEP-STATE.git
cd DEEP-STATE
# Open v4.html directly in a browser — no server needed

# To update OSINT data:
pip install -r requirements.txt
python3 scraper.py
```

---

## Disclaimer

This project uses **publicly available information only**. Positions marked 📡 are sourced from published news. Positions marked 〜 are estimated from open-source operational doctrine and should not be taken as accurate real-time positions. For educational and research purposes only.

---

⭐ **Star this repo** if you find it useful — it helps others discover the project.
