#!/usr/bin/env python3
"""
Web scraper for Arknights Wiki to extract operator data
Crawls operator pages and downloads images
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class ArknightsScraper:
    def __init__(self, rarity: int, scrape_skins: bool = False):
        self.rarity = rarity
        self.scrape_skins = scrape_skins
        self.base_url = f"https://arknights.wiki.gg/wiki/Operator/{rarity}-star"
        self.data_dir = Path("data")
        self.default_dir = Path("default")
        self.all_dir = Path("all")
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.default_dir.mkdir(exist_ok=True)
        if scrape_skins:
            self.all_dir.mkdir(exist_ok=True)
        
        # CloudScraper session for fast Cloudflare bypass
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )

    def sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing special characters"""
        return re.sub(r'[^\w\-.]', '', name.lower().replace(' ', '-').replace("'", ''))

    def fetch_with_browser(self, url: str) -> str:
        """Fetch page content using Playwright to bypass Cloudflare"""
        print(f"      🌐 Using browser to fetch: {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=30000)
                html = page.content()
                return html
            finally:
                browser.close()

    def fetch_html(self, url: str) -> str:
        """Fetch HTML with cloudscraper (fast Cloudflare bypass)"""
        print(f"    📡 Fetching: {url}")
        try:
            # CloudScraper automatically handles Cloudflare challenges (fast!)
            response = self.scraper.get(url, timeout=30)
            return response.text
        except Exception as e:
            print(f"      ⚠️  CloudScraper failed: {e}, trying browser...")
            return self.fetch_with_browser(url)

    def download_image(self, url: str, filepath: Path, retries: int = 2) -> bool:
        """Download image with retry logic using cloudscraper"""
        if not url.startswith('http'):
            url = 'https:' + url if url.startswith('//') else urljoin('https://arknights.wiki.gg', url)
        
        print(f"      📥 Downloading: {filepath.name} from {url[:60]}...")
        
        for attempt in range(retries + 1):
            try:
                start = time.time()
                response = self.scraper.get(url, timeout=30)
                
                if response.status_code == 200:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_bytes(response.content)
                    elapsed = int((time.time() - start) * 1000)
                    size_kb = len(response.content) / 1024
                    print(f"      ✅ Saved: {filepath.name} ({size_kb:.1f}KB, {elapsed}ms)")
                    return True
                    
            except Exception as e:
                print(f"      ⚠️  Attempt {attempt + 1}/{retries + 1} failed: {e}")
                if attempt < retries:
                    wait = (attempt + 1) * 1000
                    print(f"      ⏱️  Waiting {wait}ms before retry...")
                    time.sleep(wait / 1000)
        
        print(f"      ❌ Download failed after {retries + 1} attempts")
        return False

    def scrape_operator_list(self) -> List[Dict]:
        """Scrape the operator list page"""
        print(f"\n🎯 Starting scrape for {self.base_url}")
        print(f"⭐ Rarity: {self.rarity}★")
        
        html = self.fetch_html(self.base_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        operators = []
        
        # Find the operator table
        table = soup.find('table', class_='wikitable') or soup.find('table', class_='sortable')
        
        if not table:
            print("⚠️  No table found, trying alternative selectors...")
            table = soup.find('table')
        
        if not table:
            print("❌ Could not find operator table")
            return operators
        
        rows = table.find_all('tr')[1:]  # Skip header
        print(f"📊 Found {len(rows)} operators")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            
            # Extract name
            name_cell = cells[0]
            name_link = name_cell.find('a')
            if not name_link:
                continue
            
            name = name_link.get_text().strip()
            
            # Extract image
            img = name_cell.find('img') or cells[0].find('img')
            image_url = img.get('src') or img.get('data-src') if img else None
            
            if name and image_url:
                op_id = self.sanitize_filename(name)
                operators.append({
                    'id': op_id,
                    'name': name,
                    'rarity': self.rarity,
                    'imageUrl': image_url
                })
        
        print(f"✅ Scraped {len(operators)} operators")
        return operators

    def scrape_operator_skins(self, operator: Dict) -> List[Dict]:
        """Scrape all skins for an operator"""
        url = f"https://arknights.wiki.gg/wiki/{operator['name'].replace(' ', '_')}"
        
        try:
            html = self.fetch_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            skins = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src', '')
                if 'avatar' in src:
                    src = src.split('?')[0]
                    alt = img.get('alt', '')
                    skin_name = alt or Path(src).stem
                    
                    if 'default' not in skin_name.lower():
                        skins.append({
                            'name': skin_name,
                            'url': src,
                            'filename': f"{self.sanitize_filename(skin_name)}.png"
                        })
            
            return skins
        except Exception as e:
            print(f"      ⚠️  Error scraping skins: {e}")
            return []

    def process_operators(self, operators: List[Dict]) -> None:
        """Download images for all operators (always rescrape for new skins)"""
        print(f"\n📸 Processing {len(operators)} operator images...")
        
        for idx, op in enumerate(operators, 1):
            print(f"\n  [{idx}/{len(operators)}] Processing: {op['name']} ({op['id']})")
            
            # Download default image (skip if exists to save time)
            default_path = self.default_dir / f"{op['id']}.png"
            if default_path.exists():
                print(f"    ⏭️  Default image already exists")
            else:
                self.download_image(op['imageUrl'], default_path)
            
            # Download skins if enabled (ALWAYS scrape to check for new skins)
            if self.scrape_skins:
                print(f"    🎨 Processing skins for {op['name']}...")
                op_dir = self.all_dir / op['id']
                op_dir.mkdir(exist_ok=True)
                
                # Copy default skin
                default_skin = op_dir / 'default.png'
                if not default_skin.exists() and default_path.exists():
                    import shutil
                    shutil.copy(default_path, default_skin)
                
                # ALWAYS scrape skins (operators may have new skins)
                skins = self.scrape_operator_skins(op)
                
                # Only download skins we don't have yet
                for skin in skins:
                    skin_path = op_dir / skin['filename']
                    if not skin_path.exists():
                        self.download_image(skin['url'], skin_path)
                    else:
                        print(f"      ⏭️  {skin['filename']} already exists")
            
            # Brief pause between operators
            if idx < len(operators):
                time.sleep(0.1)  # Reduced from 0.2s for speed
        
        print(f"\n✅ Processing complete!")

    def save_data(self, operators: List[Dict]) -> None:
        """Save operator data to JSON"""
        output_file = self.data_dir / f"operators-{self.rarity}star.json"
        print(f"\n💾 Saving data to {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(operators, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(operators)} operators")

    def run(self) -> None:
        """Main scraping workflow"""
        try:
            operators = self.scrape_operator_list()
            if operators:
                self.process_operators(operators)
                self.save_data(operators)
                print(f"\n🎉 Successfully scraped {len(operators)} {self.rarity}-star operators!")
            else:
                print("❌ No operators found")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Scrape Arknights operator data')
    parser.add_argument('rarity', type=int, choices=[1, 2, 3, 4, 5, 6], 
                       help='Operator rarity (1-6)')
    parser.add_argument('--skins', '-s', action='store_true',
                       help='Also scrape all operator skins')
    
    args = parser.parse_args()
    
    scraper = ArknightsScraper(args.rarity, args.skins)
    scraper.run()


if __name__ == '__main__':
    main()
