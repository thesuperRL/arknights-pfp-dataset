# Arknights Operator Profile Pictures Dataset

This repository contains all operator profile pictures crawled from the Arknights Wiki, plus the scraper to keep them updated.

## Structure

```
arknights-pfp-dataset/
├── default/            # Default image set (420+ operator profile pictures)
│   ├── silverash.png
│   ├── amiya.png
│   └── ...
├── all/                # Complete collection with all skins (optional)
│   ├── silverash/
│   │   ├── default.png
│   │   ├── winter-messenger.png
│   │   └── ...
│   ├── amiya/
│   │   ├── default.png
│   │   └── ...
│   └── ...
├── scraper.ts          # Web scraper for downloading operator images
├── package.json        # Dependencies for the scraper
├── data/               # Temporary JSON data (gitignored)
└── README.md
```

- **default/**: Quick-access folder with just the default operator images (`{operator-id}.png`)
- **all/**: Complete collection organized by operator, including all skins/outfits

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

### Running Manually

Run the scraper with Python:

```bash
# Scrape 6-star operators with skins
python scraper.py 6 --skins

# Scrape without skins (defaults only)
python scraper.py 6

# Other rarities
python scraper.py 1 --skins
python scraper.py 5 --skins
```

## Updating Images

Run the scraper to download operator images:

```bash
# Scrape specific rarity with all skins
python scraper.py 6 --skins
python scraper.py 5 --skins

# Scrape all rarities with skins
for i in {1..6}; do python scraper.py $i --skins; done

# Scrape defaults only (without skins)
python scraper.py 6
```

The scraper will:
1. Fetch operator data from Arknights Wiki
2. Download profile images that don't already exist
3. Skip images that are already downloaded
4. **Default mode**: Save images to `default/` directory as `{operator-id}.png`
5. **Skins mode** (`--skins`): Also create `all/{operator-id}/` folders with all skins including default

## Updating Images

**Note:** Due to Cloudflare protection, the scraper must be run locally. See [SCRAPING.md](SCRAPING.md) for detailed instructions.

### Quick Start

```bash
# Setup (one-time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox

# Run scraper
./scrape_all.sh

# Commit changes
git add default/*.png all/*/*.png data/*.json
git commit -m "Update operator images"
git push
```

## Committing Updates

After scraping new images:

```bash
git add default/*.png
# If you scraped skins:
git add all/*/*.png
git commit -m "Add new operator images"
git push
```

## Usage in Other Projects

This repository is used as a git submodule in the [arknights-website](https://github.com/thesuperRL/arknights-website) repository at `public/images/operators/`.

To use as a submodule:

```bash
git submodule add git@github.com:thesuperRL/arknights-pfp-dataset.git path/to/images
```

## Dataset Info

- **Total Images**: 420+ operator profile pictures
- **Source**: [Arknights Wiki](https://arknights.wiki.gg)
- **Format**: PNG
- **Size**: ~7.2MB total
- **Naming**: Lowercase operator ID (e.g., `silverash.png`, `ch_en.png`)
