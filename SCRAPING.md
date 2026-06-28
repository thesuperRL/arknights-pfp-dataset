# Running the Scraper Locally

The scraper uses Firefox to bypass Cloudflare protection. It works reliably locally but is blocked in CI environments.

## Setup (One-time)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Firefox browser for Playwright
playwright install firefox
```

## Running the Scraper

### Scrape All Rarities with Skins

```bash
# Activate virtual environment
source .venv/bin/activate

# Scrape each rarity (with all skins)
python scraper.py 1 --skins
python scraper.py 2 --skins
python scraper.py 3 --skins
python scraper.py 4 --skins
python scraper.py 5 --skins
python scraper.py 6 --skins
```

### Or Use the Helper Script

```bash
source .venv/bin/activate
chmod +x scrape_all.sh
./scrape_all.sh
```

## What It Does

1. Fetches operator list pages from Arknights Wiki
2. Uses Firefox to bypass Cloudflare protection (~1s per page)
3. Downloads default operator images to `default/`
4. Scrapes individual operator pages for all skins
5. Downloads skins to `all/{operator-id}/`
6. Saves operator data to `data/operators-{rarity}star.json`

## Expected Timing

- Each rarity: 30s - 2min (depending on number of new operators/skins)
- Full scrape (all rarities): 5-10 minutes

## After Scraping

Commit and push the new images:

```bash
git add default/*.png all/*/*.png data/*.json
git commit -m "Update operator images and skins"
git push
```

## Troubleshooting

**"Module not found" errors:**
- Make sure virtual environment is activated: `source .venv/bin/activate`

**"Firefox not found" errors:**
- Run: `playwright install firefox`

**Cloudflare still blocking:**
- Make sure Firefox is installed (not Chromium)
- Firefox bypasses Cloudflare much better than Chromium
- If still blocked, wait a few minutes and try again
