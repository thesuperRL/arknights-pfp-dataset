# Arknights Operator Profile Pictures Dataset

This repository contains all operator profile pictures crawled from the Arknights Wiki.

## Structure

All operator profile pictures are stored in the root directory, named as `{operator-id}.png` (e.g., `silverash.png`, `amiya.png`).

## Usage

This repository is used as a git submodule in the main arknights-website repository at `public/images/operators/`.

## Updating Images

Images are automatically downloaded and updated by the scraper in the main website repository:

1. From the website repo, run the scraper: `npm run scrape:6star` (or other rarity)
2. New images are saved directly to this submodule directory
3. Commit and push changes in this dataset repo
4. Update the submodule reference in the website repo

## Workflow for Manual Updates

```bash
# In the arknights-pfp-dataset directory
git add .
git commit -m "Add/update operator images"
git push

# In the arknights-website directory
cd public/images/operators
git pull
cd ../../..
git add public/images/operators
git commit -m "Update operator images submodule"
git push
```
