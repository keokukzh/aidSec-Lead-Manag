import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def scrape_company_info(self, url: str) -> Dict[str, Optional[str]]:
        """
        Scrape a company's website for 'About Us', 'Mission Statement', and generic metadata.
        If AGENT1_URL is configured, routes the heavy scraping task to the external OpenClaw Agent.
        """
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        agent1_url = os.getenv("AGENT1_URL")
        agent_api_key = os.getenv("AGENT_API_KEY", "")

        if agent1_url:
            try:
                # Route to external OpenClaw agent
                logger.info(f"Routing scrape request for {url} to Agent 1 ({agent1_url})")
                resp = self.session.post(
                    f"{agent1_url}/api/v1/tools/scrape",
                    json={"url": url},
                    headers={"Authorization": f"Bearer {agent_api_key}"} if agent_api_key else {},
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "about_us": data.get("about_us"),
                        "mission_statement": data.get("mission_statement"),
                        "services_offered": data.get("services_offered")
                    }
                else:
                    logger.warning(f"Agent 1 scraping failed with {resp.status_code}: {resp.text}. Falling back to local.")
            except Exception as e:
                logger.error(f"Failed to connect to Agent 1 at {agent1_url}: {e}. Falling back to local.")

        result = {
            "about_us": None,
            "mission_statement": None,
            "services_offered": None
        }

        try:
            # 1. Fetch homepage
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            base_url = response.url
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract basic info from homepage
            result["mission_statement"] = self._extract_mission(soup)
            
            # 2. Look for about / team page
            about_url = self._find_about_page(soup, base_url)
            if about_url:
                try:
                    about_resp = self.session.get(about_url, timeout=10)
                    about_soup = BeautifulSoup(about_resp.text, "lxml")
                    result["about_us"] = self._extract_best_paragraphs(about_soup)
                except Exception as e:
                    logger.warning(f"Error scraping about page {about_url}: {e}")
            
            # If no about_us found from an about page, fallback to homepage
            if not result["about_us"]:
                result["about_us"] = self._extract_best_paragraphs(soup)
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return result

    def _find_about_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Attempt to find a link pointing to an 'About' or 'Team' page."""
        keywords = ['about', 'über uns', 'team', 'profil', 'unternehmen', 'wer wir sind']
        for a in soup.find_all('a', href=True):
            text = a.get_text().lower()
            href = a['href'].lower()
            if any(k in text for k in keywords) or any(k in href for k in keywords):
                full_url = urljoin(base_url, a['href'])
                # Ensure we don't accidentally navigate out of the domain
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    return full_url
        return None

    def _extract_mission(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract mission statement usually found in header or meta tags."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'][:500]
        
        # Fallback to h1 or h2
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)[:500]
            
        return None

    def _extract_best_paragraphs(self, soup: BeautifulSoup) -> str:
        """Extract readable paragraphs, filtering out menus, footers, etc."""
        # Try to focus on main content area
        main_content = soup.find('main') or soup.find(id='content') or soup.find(class_='content') or soup
        
        paragraphs = []
        for p in main_content.find_all('p'):
            text = p.get_text(strip=True)
            # Filter extremely short or overly long paragraphs (likely scripts/styles if not parsed properly)
            if len(text) > 50 and len(text) < 1000:
                paragraphs.append(text)
        
        # Join top 3 paragraphs to prevent huge payloads
        return "\n\n".join(paragraphs[:3])

# Singleton instance
_scraper_service = None

def get_scraper_service() -> ScraperService:
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service
