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
    def __init__(self, rarity: int, scrape_skins: bool = False, operator_filter: Optional[str] = None):
        self.rarity = rarity
        self.scrape_skins = scrape_skins
        self.operator_filter = operator_filter
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

    def download_image_with_browser(self, url: str, filepath: Path) -> bool:
        """Download image using Playwright when cloudscraper fails"""
        print(f"        🌐 Using browser to download image...")
        try:
            with sync_playwright() as p:
                # Try Firefox first (better Cloudflare bypass)
                try:
                    browser = p.firefox.launch(headless=True)
                except Exception:
                    browser = p.chromium.launch(headless=True)
                
                context = browser.new_context()
                page = context.new_page()
                
                # Navigate and wait for network idle
                response = page.goto(url, wait_until='networkidle', timeout=30000)
                
                if response and response.status == 200:
                    # Get the image content from the response
                    content = response.body()
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_bytes(content)
                    size_kb = len(content) / 1024
                    print(f"        ✅ Browser download: {filepath.name} ({size_kb:.1f}KB)")
                    browser.close()
                    return True
                else:
                    print(f"        ⚠️  Browser got status: {response.status if response else 'None'}")
                    browser.close()
                    return False
                    
        except Exception as e:
            print(f"        ⚠️  Browser download failed: {str(e)[:60]}")
            return False

    def download_image(self, url: str, filepath: Path, retries: int = 2) -> bool:
        """Download image with retry logic using cloudscraper, fallback to browser"""
        # Fix relative URLs
        if not url.startswith('http'):
            if url.startswith('//'):
                url = 'https:' + url
            else:
                url = urljoin('https://arknights.wiki.gg', url)
        
        print(f"        📥 URL: {url[:80]}...")
        
        # Try cloudscraper first
        for attempt in range(retries + 1):
            try:
                start = time.time()
                response = self.scraper.get(url, timeout=30)
                
                print(f"        📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_bytes(response.content)
                    elapsed = int((time.time() - start) * 1000)
                    size_kb = len(response.content) / 1024
                    print(f"        ✅ Saved: {filepath.name} ({size_kb:.1f}KB, {elapsed}ms)")
                    return True
                elif response.status_code == 403:
                    print(f"        ⚠️  Cloudflare blocked (403), trying browser...")
                    # Fallback to browser
                    return self.download_image_with_browser(url, filepath)
                else:
                    print(f"        ⚠️  HTTP {response.status_code}")
                    if attempt == retries:
                        # Last attempt - try browser
                        return self.download_image_with_browser(url, filepath)
                    
            except Exception as e:
                print(f"        ⚠️  Error: {str(e)[:60]}")
                if attempt < retries:
                    wait = (attempt + 1) * 1000
                    time.sleep(wait / 1000)
                else:
                    # Last attempt failed - try browser
                    return self.download_image_with_browser(url, filepath)
        
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
                # Look for icon images (profile pictures): default, elite 2, and skin icons
                if '_icon' in src.lower() and (
                    'skin' in src.lower() or 
                    'elite' in src.lower() or
                    operator['name'].replace(' ', '_').lower() in src.lower()
                ):
                    skin_count += 1
                    # Clean URL (remove query params)
                    clean_src = src.split('?')[0]
                    alt = img.get('alt', '')
                    skin_name = alt or Path(clean_src).stem
                    
                    print(f"        🎨 Found icon: {skin_name[:50]}")
                    
                    # Remove .png from name before adding it back (avoid .png.png)
                    base_name = skin_name.replace('.png', '').replace('.PNG', '')
                    skins.append({
                        'name': skin_name,
                        'url': src,  # Keep query params for actual download
                        'filename': f"{self.sanitize_filename(base_name)}.png"
                    })
            
            print(f"      ✅ Found {skin_count} icon images")
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
                print(f"      📁 Operator folder: {op_dir}")
                
                # Copy default skin
                default_skin = op_dir / 'default.png'
                if not default_skin.exists() and default_path.exists():
                    import shutil
                    shutil.copy(default_path, default_skin)
                    print(f"      📋 Copied default skin")
                elif default_skin.exists():
                    print(f"      ⏭️  Default skin already exists")
                
                # ALWAYS scrape skins (operators may have new skins)
                skins = self.scrape_operator_skins(op)
                
                if not skins:
                    print(f"      ℹ️  No skins found for this operator")
                else:
                    print(f"      📥 Attempting to download {len(skins)} skins...")
                    # Only download skins we don't have yet
                    downloaded = 0
                    for skin in skins:
                        skin_path = op_dir / skin['filename']
                        if not skin_path.exists():
                            print(f"      ⬇️  Downloading {skin['filename']}...")
                            success = self.download_image(skin['url'], skin_path)
                            if success:
                                downloaded += 1
                        else:
                            print(f"      ⏭️  {skin['filename']} already exists")
                    print(f"      ✅ Downloaded {downloaded}/{len(skins)} new skins")
            
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
            
            # Filter for specific operator if requested
            if self.operator_filter:
                filter_lower = self.operator_filter.lower()
                operators = [
                    op for op in operators 
                    if filter_lower in op['name'].lower() or filter_lower in op['id'].lower()
                ]
                if not operators:
                    print(f"❌ No operator found matching '{self.operator_filter}'")
                    sys.exit(1)
                print(f"🎯 Filtering to {len(operators)} operator(s) matching '{self.operator_filter}'")
            
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
    parser.add_argument('--operator', '-o', type=str,
                       help='Scrape only this specific operator (by name)')
    
    args = parser.parse_args()
    
    scraper = ArknightsScraper(args.rarity, args.skins, operator_filter=args.operator)
    scraper.run()


if __name__ == '__main__':
    main()
