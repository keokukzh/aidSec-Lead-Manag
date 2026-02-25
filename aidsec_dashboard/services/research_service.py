"""Research Service for automated web scraping of lead contact information."""
import logging
import re
import warnings
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

# Suppress SSL warnings for scraping
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

logger = logging.getLogger(__name__)

# Common email patterns
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Common phone patterns (Swiss/German format)
PHONE_PATTERN = re.compile(
    r'(?:\+?41|0)\s?[0-9]{2,3}[\s.-]?[0-9]{3}[\s.-]?[0-9]{2}[\s.-]?[0-9]{2}'
)

# Common contact page paths
CONTACT_PATHS = [
    '/contact', '/kontakt', '/impressum', '/about', '/uber-uns',
    '/team', '/contact-us', '/contact-us.html', '/contact.html',
    '/kontakt.html', '/impressum.html'
]

# Common email contact links
EMAIL_LINKS = [
    'mailto:', 'contact@', 'info@', 'support@', 'kontakt@'
]


class ResearchService:
    """Service for automated data collection from lead websites."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def research_lead(self, url: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Research a lead's website to collect contact information.

        Args:
            url: The website URL to research
            company_name: Optional company name for better context

        Returns:
            Dictionary with collected data:
            - email: Email address if found
            - phone: Phone number if found
            - contact_name: Contact person name if found
            - address: Physical address if found
            - linkedin: LinkedIn URL if found
            - xing: Xing URL if found
            - meta: Additional metadata
        """
        if not url:
            return self._empty_result(error="No URL provided")

        # Normalize URL
        url = self._normalize_url(url)

        results = {
            "email": None,
            "phone": None,
            "contact_name": None,
            "address": None,
            "linkedin": None,
            "xing": None,
            "meta": {},
            "error": None,
            "pages_checked": []
        }

        try:
            # First try the main page
            main_page_data = self._scrape_page(url)
            results.update(main_page_data)
            results["pages_checked"].append(url)

            # If no email found, try contact pages
            if not results.get("email") or not results.get("phone"):
                contact_data = self._try_contact_pages(url)
                if contact_data:
                    results["pages_checked"].extend(contact_data.get("pages_checked", []))
                    for key in ["email", "phone", "contact_name", "address"]:
                        if not results.get(key) and contact_data.get(key):
                            results[key] = contact_data[key]

            # Look for social links
            if not results.get("linkedin") or not results.get("xing"):
                social_data = self._find_social_links(url)
                results["linkedin"] = results["linkedin"] or social_data.get("linkedin")
                results["xing"] = results["xing"] or social_data.get("xing")

            # Add metadata
            results["meta"] = {
                "researched_at": datetime.utcnow().isoformat(),
                "url": url,
                "company_name": company_name
            }

        except Exception as e:
            logger.error(f"Error researching {url}: {str(e)}")
            results["error"] = str(e)

        return results

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure it has a scheme."""
        if not url:
            return ""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url

    def _empty_result(self, error: str = None) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "email": None,
            "phone": None,
            "contact_name": None,
            "address": None,
            "linkedin": None,
            "xing": None,
            "meta": {},
            "error": error,
            "pages_checked": []
        }

    def _scrape_page(self, url: str) -> Dict[str, Any]:
        """Scrape a single page for contact information."""
        result = {
            "email": None,
            "phone": None,
            "contact_name": None,
            "address": None,
            "linkedin": None,
            "xing": None,
            "pages_checked": []
        }

        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find email
            if not result.get("email"):
                result["email"] = self._find_email(soup, url)

            # Find phone
            if not result.get("phone"):
                result["phone"] = self._find_phone(soup)

            # Find address
            if not result.get("address"):
                result["address"] = self._find_address(soup)

            # Find social links
            social = self._extract_social_links(soup, url)
            result["linkedin"] = social.get("linkedin")
            result["xing"] = social.get("xing")

        except requests.RequestException as e:
            logger.warning(f"Failed to scrape {url}: {e}")

        return result

    def _find_email(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find email address on page."""
        # Check mailto links
        mailto_links = soup.find_all('a', href=re.compile('^mailto:'))
        for link in mailto_links:
            href = link.get('href', '')
            email = re.search(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', href)
            if email:
                return email.group(1)

        # Check visible text
        page_text = soup.get_text()
        emails = EMAIL_PATTERN.findall(page_text)
        for email in emails:
            # Filter out common non-contact emails
            if not any(skip in email.lower() for skip in ['example', 'test@', 'noreply', 'no-reply']):
                return email

        return None

    def _find_phone(self, soup: BeautifulSoup) -> Optional[str]:
        """Find phone number on page."""
        page_text = soup.get_text()
        phones = PHONE_PATTERN.findall(page_text)
        if phones:
            # Return first valid phone
            return phones[0]

        # Also check tel: links
        tel_links = soup.find_all('a', href=re.compile('^tel:'))
        if tel_links:
            return tel_links[0].get('href', '').replace('tel:', '')

        return None

    def _find_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Find physical address on page."""
        # Look for address tags
        address_tags = soup.find_all('address')
        for tag in address_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 5:
                return text

        # Look for common address patterns in divs
        address_divs = soup.find_all('div', class_=re.compile(r'address', re.I))
        for div in address_divs:
            text = div.get_text(strip=True)
            if text and len(text) > 5:
                return text

        return None

    def _try_contact_pages(self, base_url: str) -> Dict[str, Any]:
        """Try common contact page paths."""
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        result = {
            "email": None,
            "phone": None,
            "contact_name": None,
            "address": None,
            "pages_checked": []
        }

        for path in CONTACT_PATHS:
            url = urljoin(base, path)
            try:
                response = requests.get(url, headers=self.headers, timeout=5, verify=False)
                if response.status_code == 200:
                    result["pages_checked"].append(url)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    if not result.get("email"):
                        result["email"] = self._find_email(soup, url)
                    if not result.get("phone"):
                        result["phone"] = self._find_phone(soup)
                    if not result.get("address"):
                        result["address"] = self._find_address(soup)

                    # If we found data, can stop
                    if result.get("email") and result.get("phone"):
                        break

            except requests.RequestException:
                continue

        return result

    def _find_social_links(self, base_url: str) -> Dict[str, Optional[str]]:
        """Find social media links from main page."""
        result = {"linkedin": None, "xing": None}

        try:
            response = requests.get(base_url, headers=self.headers, timeout=self.timeout, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            return self._extract_social_links(soup, base_url)
        except requests.RequestException:
            return result

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
        """Extract social media links from soup."""
        result = {"linkedin": None, "xing": None}

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()

            if 'linkedin.com' in href:
                result["linkedin"] = link.get('href')
            elif 'xing.com' in href:
                result["xing"] = link.get('href')

        return result


# Singleton instance
research_service = ResearchService()


def get_research_service() -> ResearchService:
    """Get the research service instance."""
    return research_service
