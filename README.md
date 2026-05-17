# 🌊 DEEP STATE — Real-Time Submarine Tracker

**Live global submarine intelligence map powered by OSINT**

🔗 **[deepstate.live → Launch App](https://qmfire18-source.github.io/DEEP-STATE/)**

---

![Deep State Preview](https://qmfire18-source.github.io/DEEP-STATE/v4.html)

## What is Deep State?

**Deep State** is an open-source, real-time submarine tracking platform aggregating public OSINT (Open Source Intelligence) data from military analysts, naval news outlets and satellite imagery reports.

Track **37 submarines** across **22 nations** — including nuclear SSBNs, attack SSNs and conventional diesel-electric boats — updated automatically every 6 hours.

---

## Features

- 🗺️ **Interactive map** — zoom, click any submarine for full specs
- 🌐 **3D globe view** — real-time rotating Earth with submarine positions
- 📡 **Live OSINT feed** — auto-scraped from USNI News, HI Sutton, Naval News
- ☢️ **Nuclear deployment level** — live threat assessment bar
- 🔍 **Search & filters** — by type (SSN / SSBN / SSGN / SS), nation, nuclear status
- 🇫🇷 🇬🇧 **Bilingual** — French / English interface
- 📊 **Fleet comparison** — top 14 submarine fleets ranked by size

---

## Submarines Tracked

| Nation | Class | Type |
|--------|-------|------|
| 🇺🇸 United States | Ohio, Virginia, Seawolf | SSBN / SSN / SSGN |
| 🇷🇺 Russia | Borei, Yasen, Oscar II, Kilo | SSBN / SSN / SSGN / SS |
| 🇨🇳 China | Jin (Type 094), Shang (Type 093) | SSBN / SSN |
| 🇬🇧 United Kingdom | Vanguard, Astute | SSBN / SSN |
| 🇫🇷 France | Triomphant, Barracuda | SSBN / SSN |
| 🇮🇳 India | Arihant | SSBN |
| 🇩🇪 Germany | Type 212A | SS |
| 🇯🇵 Japan | Sōryū | SS |
| + 14 more nations | | |

---

## Data Sources

All positions are **estimated** from public sources. No classified data is used.

- [USNI News Fleet Tracker](https://news.usni.org/category/fleet-tracker)
- [USNI News Western Pacific Pulse](https://news.usni.org/category/news/western-pacific-pulse)
- [HI Sutton — Covert Shores](https://www.hisutton.com)
- [Naval News](https://www.navalnews.com)
- [IISS Military Balance 2025](https://www.iiss.org/publications/the-military-balance/)

---

## Auto-Update

The scraper runs every **6 hours** via GitHub Actions, pulling the latest sightings from naval intelligence RSS feeds and updating submarine positions automatically.

---

## Tech Stack

- Pure **HTML / CSS / JavaScript** — zero backend, zero framework
- [Leaflet.js](https://leafletjs.com/) — interactive map
- [Three.js](https://threejs.org/) — 3D globe
- **Python 3** scraper with feedparser + BeautifulSoup
- **GitHub Actions** — automated OSINT scraping & deployment
- **GitHub Pages** — free hosting

---

## Keywords

submarine tracker, OSINT submarine, naval intelligence map, real-time submarine map, submarine positions, nuclear submarine tracker, military submarine OSINT, naval tracker, sous-marin tracker, carte sous-marins, OSINT naval, suivi sous-marins en temps réel, submarine geopolitics, ssbn tracker, ssn tracker, navy intelligence

---

## Disclaimer

This project uses only **publicly available** information. All positions are **estimates** based on open-source reporting and should not be taken as accurate real-time positions. For educational and informational purposes only.

---

⭐ **Star this repo** if you find it useful — it helps others discover the project.
