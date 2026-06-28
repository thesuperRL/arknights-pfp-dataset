#!/bin/bash
# Scrape all operator rarities with skins

set -e

echo "🚀 Starting full operator scrape (all rarities with skins)"
echo ""

for rarity in {1..6}; do
    echo "⭐ Scraping ${rarity}-star operators..."
    python scraper.py $rarity --skins
    echo ""
done

echo "✅ All rarities scraped!"
echo ""
echo "📊 Summary:"
echo "  Default images: $(ls default/*.png 2>/dev/null | wc -l) files"
echo "  Operator folders: $(ls -d all/*/ 2>/dev/null | wc -l) folders"
echo ""
echo "💡 To commit:"
echo "  git add default/*.png all/*/*.png data/*.json"
echo "  git commit -m 'Update operator images and skins'"
echo "  git push"
