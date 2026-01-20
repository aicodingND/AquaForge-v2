import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict

class SetonScraper:
    """Scraper for setonswimming.org meet results."""
    
    BASE_URL = "https://setonswimming.org"
    RESULTS_CATEGORY_URL = "https://setonswimming.org/category/meet-results/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_latest_meet_posts(self, limit: int = 3) -> List[Dict[str, str]]:
        """Fetch the latest N posts from the Meet Results category."""
        try:
            response = self.session.get(self.RESULTS_CATEGORY_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            posts = []
            # This selector might need adjustment based on actual theme structure
            # Typically WordPress uses <article> or .post
            articles = soup.find_all('article')
            
            for article in articles[:limit]:
                title_elem = article.find('h2', class_='entry-title')
                if not title_elem:
                    continue
                    
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                    
                posts.append({
                    'title': link_elem.get_text(strip=True),
                    'url': link_elem['href']
                })
                
            return posts
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return []

    def extract_pdf_links(self, post_url: str) -> List[Dict[str, str]]:
        """Find all PDF links in a specific meet post."""
        try:
            response = self.session.get(post_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            pdf_links = []
            # Find all links ending in .pdf
            for link in soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE)):
                pdf_links.append({
                    'text': link.get_text(strip=True),
                    'url': link['href'],
                    'filename': link['href'].split('/')[-1]
                })
                
            return pdf_links
        except Exception as e:
            print(f"Error extracting PDFs from {post_url}: {e}")
            return []

class BrowserManager:
    """Manager for Playwright browser interactions (Placeholder for Phase 2)."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        
    async def start(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        # Use simple browser request for now, can be chromium/firefox
        self.browser = await self.playwright.chromium.launch(headless=True)
        
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Singleton instance
scraper = SetonScraper()
