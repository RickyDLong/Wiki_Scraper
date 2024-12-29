# Imports
import csv
import os
import random
import time
import warnings
from threading import Thread, Lock
from pathlib import Path

import urllib3
import requests
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from rich import print
from rich.live import Live
from rich.progress import track
from rich.table import Table

# Suppress warnings and setup session
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = CachedSession('item_cache', backend='sqlite', expire_after=3600)

class ItemCategories:
    """Item category definitions and mappings"""
    WEAPONS = {
        '1h': '1H_Weapons',
        '2h': '2H_Weapons',
        'piercing': 'Piercing',
        'blunt': 'Blunt',
        'slashing': 'Slashing',
        'bow': 'Bows',
        'throwing': 'Throwing'
    }
    
    EQUIPMENT = {
        'arms': 'Arms',
        'back': 'Back',
        'chest': 'Chest',
        'ear': 'Ears',
        'face': 'Face',
        'feet': 'Feet',
        'fingers': 'Fingers',
        'hands': 'Hands',
        'head': 'Head',
        'legs': 'Legs',
        'neck': 'Neck',
        'shield': 'Shields',
        'shoulders': 'Shoulders',
        'waist': 'Waist',
        'wrist': 'Wrist'
    }

class Item:
    """Base class for EverQuest items"""
    def __init__(self, name):
        self.name = name
        self.attributes = {}

    def to_dict(self):
        """Convert item to dictionary"""
        return {
            "Name": self.name,
            **self.attributes
        }

class Weapon(Item):
    """Weapon specific item class"""
    FIELDS = [
        "Name", "Type", "Damage", "Delay", "Classes", "Races",
        "Skill", "Effect", "WT", "Size", "Magic Item",
        "Lore Item", "No Drop", "30d Avg", "90d Avg", "All Time Avg"
    ]
    
    def __init__(self, name):
        super().__init__(name)
        self.item_type = "weapon"

class Equipment(Item):
    """Equipment specific item class"""
    FIELDS = [
        "Name", "Type", "AC", "Stats", "Classes", "Races",
        "Effect", "WT", "Size", "Magic Item", "Lore Item",
        "No Drop", "30d Avg", "90d Avg", "All Time Avg"
    ]
    
    def __init__(self, name):
        super().__init__(name)
        self.item_type = "equipment"

class ItemScraper:
    """Scrapes and processes EverQuest items"""
    def __init__(self, base_url, output_dir="output"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.headers = {"User-Agent": "EverQuest Item Scraper (Educational)"}
        self.item_count = 0
        self.latest_item = None
        self.response_time = 0
        self.error_rate = 0
        self.item_types = {}
        self.lock = Lock()
        self.failed_items = []
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "weapons").mkdir(exist_ok=True)
        (self.output_dir / "equipment").mkdir(exist_ok=True)

    def _get_category_path(self, item):
        """Get output path for item category"""
        if isinstance(item, Weapon):
            base_dir = self.output_dir / "weapons"
            type_key = item.attributes.get("Type", "").lower()
            filename = next((v for k, v in ItemCategories.WEAPONS.items() 
                           if k in type_key), "misc")
        else:
            base_dir = self.output_dir / "equipment"
            slot = item.attributes.get("Slot", "").lower()
            filename = ItemCategories.EQUIPMENT.get(slot, "misc")
            
        return base_dir / f"{filename}.csv"

    def _export_items(self, items):
        """Export items to category-specific files"""
        categorized = {}
        
        # Group items by category
        for item in items:
            filepath = self._get_category_path(item)
            if filepath not in categorized:
                categorized[filepath] = []
            categorized[filepath].append(item)
        
        # Export each category
        for filepath, category_items in categorized.items():
            fields = Weapon.FIELDS if isinstance(category_items[0], Weapon) else Equipment.FIELDS
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for item in category_items:
                    writer.writerow(item.to_dict())
                    
            print(f"[green]Exported {len(category_items)} items to {filepath}[/green]")

    def scrape_items(self, urls):
        """Scrape multiple item URLs"""
        items = []
        try:
            for url in track(urls, description="Scraping items..."):
                try:
                    # Skip category pages
                    if "Category:" in url:
                        continue
                        
                    item = self.scrape_item_page(url)
                    if item and item.attributes:  # Validate item has data
                        items.append(item)
                        print(f"[green]Successfully scraped: {item.name}[/green]")
                except Exception as e:
                    print(f"[red]Error scraping {url}: {e}[/red]")
                    self.failed_items.append(url)
                    
            if items:
                print(f"\n[cyan]Found {len(items)} valid items[/cyan]")
                self._export_items(items)
            else:
                print("[yellow]No valid items found to process[/yellow]")
                
            return items
            
        except Exception as e:
            print(f"[red]Fatal error in scrape_items: {e}[/red]")
            import traceback
            print(traceback.format_exc())
            return []

    def scrape_item_page(self, url):
        """Scrape single item page"""
        try:
            response = session.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.content, "html.parser")
            
            item_data = self._parse_item_data(soup)
            if not item_data:
                return None
                
            name = url.split("/")[-1].replace("_", " ")
            item_type = self._determine_item_type(item_data)
            item = Weapon(name) if item_type == "weapon" else Equipment(name)
            item.attributes = item_data
            
            return item
            
        except Exception as e:
            print(f"[red]Error scraping {url}: {e}[/red]")
            return None

    def _parse_item_data(self, soup):
        """Parse item attributes from page"""
        try:
            data = {}
            info_box = soup.find("div", {"class": "infobox"})
            if not info_box:
                return None
                
            # Parse item properties
            for row in info_box.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) == 2:
                    key = cols[0].text.strip()
                    value = cols[1].text.strip()
                    data[key] = value
                    
            return data
            
        except Exception as e:
            print(f"[red]Error parsing item data: {e}[/red]")
            return None

    def _determine_item_type(self, item_data):
        """Determine if item is weapon or equipment"""
        if not item_data:
            return "equipment"
            
        item_type = item_data.get("Type", "").lower()
        weapon_types = ["1h", "2h", "bow", "throwing", "piercing", "blunt", "slashing"]
        return "weapon" if any(t in item_type for t in weapon_types) else "equipment"

    def _extract_category_items(self, category_url):
        """Extract items from category pages"""
        try:
            links = set()
            last_item = None
            
            while True:
                url = category_url
                if last_item:
                    url += f"?pagefrom={last_item}"
                
                response = session.get(url, headers=self.headers, verify=False)
                if response.status_code != 200:
                    break
                    
                soup = BeautifulSoup(response.content, "html.parser")
                content = soup.find("div", {"id": "mw-content-text"})
                if not content:
                    break
                    
                items = content.find_all("a", href=True)
                found_items = False
                last_item_this_page = None
                
                for item in items:
                    href = item.get("href", "")
                    if any(x in href for x in ["/Category:", "Special:", "File:", "Discussion:",
                                            "Help:", "User:", "Template:", "Project:"]):
                        continue
                        
                    if href.startswith("/"):
                        full_url = self.base_url + href
                        if full_url not in links:
                            links.add(full_url)
                            print(f"[cyan]Found new item:[/cyan] [yellow]{item.text}[/yellow]")
                            found_items = True
                            last_item_this_page = item.text
                
                if not found_items:
                    break
                    
                last_item = last_item_this_page
                if not last_item:
                    break
                    
                time.sleep(random.uniform(0.5, 1))
                
            return list(links)
            
        except Exception as e:
            print(f"[red]Error extracting items: {e}[/red]")
            return []


    def scrape_category(self, category_url):
        """Scrape all items in a category"""
        try:
            category_name = category_url.split('/')[-1]
            print(f"\n[bold blue]Processing category: {category_name}[/bold blue]")
            
            urls = self._extract_category_items(category_url)
            if not urls:
                print("[yellow]No items found in category![/yellow]")
                return []
                
            # Scrape items for this category
            items = []
            for url in track(urls, description=f"Scraping {category_name}..."):
                try:
                    if "Category:" in url:
                        continue
                        
                    item = self.scrape_item_page(url)
                    if item and item.attributes:
                        items.append(item)
                        
                except Exception as e:
                    print(f"[red]Error scraping {url}: {e}[/red]")
                    self.failed_items.append(url)
            
            # Export category items immediately
            if items:
                print(f"[green]Found {len(items)} items in {category_name}[/green]")
                self._export_items(items)
                
            return items
            
        except Exception as e:
            print(f"[red]Error processing category: {e}[/red]")
            return []

    def crawl_categories(self):
        """Crawl equipment categories"""
        categories = [
        # Equipment Categories
        "/Category:Arms", "/Category:Back", "/Category:Chest",
        "/Category:Ear", "/Category:Face", "/Category:Feet",
        "/Category:Fingers", "/Category:Hands", "/Category:Head",
        "/Category:Legs", "/Category:Neck", "/Category:Shoulders",
        "/Category:Waist", "/Category:Wrist",
        
        # Weapon Categories
        "/Category:Ammo", "/Category:Primary",
        "/Category:Range", "/Category:Secondary"
    ]
        
        all_items = []
        for category in categories:
            category_url = self.base_url + category
            items = self.scrape_category(category_url)
            all_items.extend(items)
            
        if not all_items:
            print("[red]No items found![/red]")
        return all_items

def main():
    """Main entry point"""
    try:
        print("\n[bold blue]Starting EverQuest Item Scraper...[/bold blue]\n")
        
        # Initialize scraper
        base_url = "https://wiki.project1999.com"
        output_dir = "output"
        
        print(f"[cyan]Base URL: {base_url}[/cyan]")
        print(f"[cyan]Output Directory: {output_dir}[/cyan]\n")
        
        # Create and run scraper
        scraper = ItemScraper(base_url, output_dir)
        items = scraper.crawl_categories()
        
        # Report results
        print(f"\n[green]Successfully processed {len(items)} items[/green]")
        if scraper.failed_items:
            print(f"[yellow]Failed to process {len(scraper.failed_items)} items[/yellow]")
            
    except Exception as e:
        print(f"[red]Fatal error: {e}[/red]")
        import traceback
        print(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())