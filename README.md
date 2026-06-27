# Arknights Operator Profile Pictures Dataset

This repository contains all operator profile pictures crawled from the Arknights Wiki, plus the scraper to keep them updated.

## Structure

```
arknights-pfp-dataset/
├── default/            # Default image set (420+ operator profile pictures)
│   ├── silverash.png
│   ├── amiya.png
│   └── ...
├── scraper.ts          # Web scraper for downloading operator images
├── package.json        # Dependencies for the scraper
├── data/               # Temporary JSON data (gitignored)
└── README.md
```

All operator profile pictures are stored in the `default/` directory, named as `{operator-id}.png`.

## Setup

Install dependencies:

```bash
npm install
```

## Updating Images

Run the scraper to download new operator images:

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

The scraper will:
1. Fetch operator data from Arknights Wiki
2. Download profile images that don't already exist
3. Skip images that are already downloaded
4. Save images to the `default/` directory as `{operator-id}.png`

## Committing Updates

After scraping new images:

```bash
git add default/*.png
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

## License

MIT
