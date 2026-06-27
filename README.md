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
npm install
```

### Running Manually

You can run the scraper in three ways:

**1. With npm scripts (easiest):**
```bash
npm run scrape:6star
```

**2. Directly with ts-node:**
```bash
npx ts-node scraper.ts 6
npx ts-node scraper.ts 6 --skins
```

**3. Compile and run with Node:**
```bash
npm run build              # Compile TypeScript to JavaScript
node dist/scraper.js 6     # Run compiled version
node dist/scraper.js 6 --skins
```

## Updating Images

### Default Images Only

Run the scraper to download new operator default images:

```bash
# Scrape all 6-star operators (most common)
npm run scrape:6star

# Or scrape other rarities
npm run scrape:1star
npm run scrape:2star
npm run scrape:3star
npm run scrape:4star
npm run scrape:5star

# Or specify rarity directly
npm run scrape -- 6
```

### All Skins (Optional)

To download ALL skins/outfits for operators (organizes in `all/` folder):

```bash
# Scrape 6-star operators with all skins
npm run scrape:skins

# Or scrape all rarities with skins (takes a while!)
npm run scrape:all-skins

# Or specify rarity with skins flag
npm run scrape -- 6 --skins
```

The scraper will:
1. Fetch operator data from Arknights Wiki
2. Download profile images that don't already exist
3. Skip images that are already downloaded
4. **Default mode**: Save images to `default/` directory as `{operator-id}.png`
5. **Skins mode** (`--skins`): Also create `all/{operator-id}/` folders with all skins including default

## Automated Updates

This repository has a GitHub Actions workflow that automatically scrapes for new operator images **including all skins** monthly (1st of each month). It can also be triggered manually from the Actions tab with an option to scrape only defaults if needed.

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
