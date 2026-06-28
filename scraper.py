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
        print(f"      ⏰ Browser start at {time.strftime('%H:%M:%S')}")
        with sync_playwright() as p:
            # Try Firefox first (sometimes bypasses Cloudflare better)
            print(f"      🦊 Launching Firefox...")
            browser = p.firefox.launch(headless=True)
            print(f"      ✓ Firefox launched")
            try:
                page = browser.new_page()
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Wait for Cloudflare challenge to complete by checking title change
                print(f"      ⏳ Waiting for Cloudflare challenge to complete...")
                max_wait = 60
                for i in range(max_wait):
                    page.wait_for_timeout(1000)
                    title = page.title()
                    if 'Just a' not in title and 'moment' not in title and 'second' not in title:
                        print(f"      ✅ Challenge passed after {i+1}s!")
                        print(f"      📄 Page title: {title}")
                        break
                    if (i + 1) % 10 == 0:
                        print(f"      ⏳ Still waiting... ({i+1}s)")
                else:
                    print(f"      ❌ Challenge did not complete after {max_wait}s")
                    print(f"      📄 Final title: {page.title()}")
                
                html = page.content()
                return html
            finally:
                browser.close()

    def fetch_html(self, url: str) -> str:
        """Fetch HTML with cloudscraper, fallback to browser if needed"""
        print(f"    📡 Fetching: {url}")
        print(f"    ⏰ Starting at {time.strftime('%H:%M:%S')}")
        try:
            # CloudScraper handles most Cloudflare challenges
            print(f"    🔄 Trying CloudScraper...")
            response = self.scraper.get(url, timeout=30)
            print(f"    ✓ CloudScraper response: {response.status_code}")
            
            # Check if we got a challenge page or empty content
            if (response.status_code == 403 or 
                'Just a second' in response.text or 
                'challenge' in response.text.lower() or
                len(response.text) < 5000):  # suspiciously small for a wiki page
                print(f"      ⚠️  Got challenge page (status {response.status_code}), using browser...")
                return self.fetch_with_browser(url)
            
            return response.text
        except Exception as e:
            print(f"      ⚠️  CloudScraper failed: {e}, trying browser...")
            return self.fetch_with_browser(url)

    def download_image(self, url: str, filepath: Path, retries: int = 2) -> bool:
        """Download image with retry logic using cloudscraper"""
        if not url.startswith('http'):
            url = 'https:' + url if url.startswith('//') else urljoin('https://arknights.wiki.gg', url)
        
        # URL is already encoded from wiki, use it as-is
        print(f"      📥 Downloading: {filepath.name}...")
        
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
                elif response.status_code == 403:
                    # Cloudflare blocking, skip this image
                    print(f"      ⚠️  Cloudflare blocked (403), skipping")
                    return False
                    
            except Exception as e:
                if attempt < retries:
                    wait = (attempt + 1) * 1000
                    time.sleep(wait / 1000)
        
        print(f"      ⚠️  Download failed, skipping")
        return False

    def scrape_operator_list(self) -> List[Dict]:
        """Scrape the operator list page"""
        print(f"\n🎯 Starting scrape for {self.base_url}")
        print(f"⭐ Rarity: {self.rarity}★")
        
        html = self.fetch_html(self.base_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Debug: print what we found
        print(f"📊 HTML length: {len(html)}")
        title = soup.find('title')
        print(f"📄 Page title: {title.get_text() if title else 'None'}")
        
        operators = []
        
        # Try multiple table selectors
        table = None
        selectors = [
            ('table', {'class': 'wikitable'}),
            ('table', {'class': 'sortable'}),
            ('table', {'class': 'article-table'}),
            ('table', {}),  # Any table
        ]
        
        for tag, attrs in selectors:
            tables = soup.find_all(tag, attrs)
            for t in tables:
                # Check if table has operator-like data (has images and links)
                if t.find('img') and t.find('a'):
                    rows = t.find_all('tr')
                    if len(rows) > 1:  # Has header + data
                        table = t
                        print(f"✅ Found table with {len(rows)} rows")
                        break
            if table:
                break
        
        if not table:
            print("⚠️  No table found, trying card-based layout...")
            
            # Debug: show what elements we have
            all_imgs = len(soup.find_all('img'))
            all_links = len(soup.find_all('a'))
            all_divs = len(soup.find_all('div'))
            print(f"📊 Found: {all_imgs} images, {all_links} links, {all_divs} divs")
            
            # Try finding operator cards/galleries instead
            cards = soup.find_all('div', class_='character-card')
            cards += soup.find_all('div', class_='operator-card')
            cards += soup.find_all('div', class_='card')
            
            print(f"📦 Found {len(cards)} cards")
            
            if cards:
                print(f"📊 Found {len(cards)} operator cards")
                for card in cards:
                    name_link = card.find('a')
                    img = card.find('img')
                    if name_link and img:
                        name = name_link.get_text().strip()
                        image_url = img.get('src') or img.get('data-src')
                        if name and image_url:
                            op_id = self.sanitize_filename(name)
                            operators.append({
                                'id': op_id,
                                'name': name,
                                'rarity': self.rarity,
                                'imageUrl': image_url
                            })
                print(f"✅ Scraped {len(operators)} operators from cards")
                return operators
            
            print("❌ Could not find operator data")
            return operators
        
        # Parse table rows
        rows = table.find_all('tr')[1:]  # Skip header
        print(f"📊 Processing {len(rows)} rows")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 1:
                continue
            
            # Look for name and image in any cell
            name = None
            image_url = None
            
            for cell in cells:
                # Try to find name from link
                if not name:
                    name_link = cell.find('a', href=True)
                    if name_link and name_link.get_text().strip():
                        name = name_link.get_text().strip()
                
                # Try to find image
                if not image_url:
                    img = cell.find('img')
                    if img:
                        image_url = img.get('src') or img.get('data-src')
            
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
        
        print(f"      🔎 Checking for skins at: {url}")
        try:
            html = self.fetch_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Debug: count all images
            all_imgs = soup.find_all('img')
            print(f"      📊 Found {len(all_imgs)} total images on page")
            
            skins = []
            skin_count = 0
            for img in all_imgs:
                src = img.get('src') or img.get('data-src', '')
                # Look for skin images (exclude icons, get full size)
                if 'skin' in src.lower() and '_icon' not in src.lower():
                    skin_count += 1
                    # Clean URL (remove query params)
                    src = src.split('?')[0]
                    alt = img.get('alt', '')
                    skin_name = alt or Path(src).stem
                    
                    print(f"        🎨 Found skin: {skin_name[:40]}")
                    
                    skins.append({
                        'name': skin_name,
                        'url': src,
                        'filename': f"{self.sanitize_filename(skin_name)}.png"
                    })
            
            print(f"      ✅ Found {skin_count} skin images (excluding icons)")
            return skins
        except Exception as e:
            print(f"      ⚠️  Error scraping skins: {e}")
            import traceback
            traceback.print_exc()
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
