"""Ranking Service - SecurityHeaders.com Integration"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from typing import Dict, List
import ssl
import socket
from urllib.parse import urlparse


class RankingService:
    """Service to check security headers using SecurityHeaders.com"""

    BASE_URL = "https://securityheaders.com"

    KNOWN_SECURITY_HEADERS = [
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Strict-Transport-Security",
        "Referrer-Policy",
        "Permissions-Policy",
        "X-XSS-Protection",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

    def check_url(self, url: str) -> Dict:
        """
        Check security headers for a given URL.
        Returns dict with score, grade, and details.
        Primary: direct header inspection of the target site.
        Fallback: SecurityHeaders.com HTML scraping.
        """
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            result = self._check_direct(url)
            if result["grade"]:
                return result
        except Exception:
            pass

        try:
            return self._check_via_site(url)
        except Exception as e:
            return {
                "url": url,
                "score": None,
                "grade": None,
                "error": str(e),
                "headers": [],
                "checked_at": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def normalize_grade(value: str | None) -> str | None:
        """Normalize external grade values to a single DB-safe letter or None."""
        if value is None:
            return None

        cleaned = str(value).strip().upper()
        if not cleaned:
            return None

        if cleaned in {"N/A", "NA", "NONE", "NULL", "ERROR", "UNKNOWN"}:
            return None

        first = cleaned[0]
        if first in {"A", "B", "C", "D", "E", "F"}:
            return first

        return None

    def _check_direct(self, url: str) -> Dict:
        """Inspect the target site's HTTP headers directly and compute a grade."""
        resp = requests.get(
            url,
            timeout=15,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}

        headers_info = []
        present_count = 0

        for hdr in self.KNOWN_SECURITY_HEADERS:
            found = resp_headers.get(hdr.lower())
            if found:
                present_count += 1
                headers_info.append({"name": hdr, "value": found, "rating": "good"})
            else:
                headers_info.append({"name": hdr, "value": "Not set", "rating": "bad"})

        total = len(self.KNOWN_SECURITY_HEADERS)
        score = int((present_count / total) * 100)

        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        return {
            "url": url,
            "score": score,
            "grade": self.normalize_grade(grade),
            "headers": headers_info,
            "checked_at": datetime.utcnow().isoformat(),
            "ssl_valid": True,  # requests didn't fail
            "cms_detected": self._detect_cms(resp),
        }

    def _detect_cms(self, response: requests.Response) -> str:
        """Simple footprinting to detect CMS like WordPress"""
        html = response.text.lower()
        if "/wp-content/" in html or "/wp-includes/" in html or "generator\" content=\"wordpress" in html:
            return "WordPress"
        if "joomla" in html:
            return "Joomla"
        if "cdn.shopify.com" in html:
            return "Shopify"
        return "Unknown"

    def _check_via_site(self, url: str) -> Dict:
        """Fallback: scrape SecurityHeaders.com with full browser headers."""
        check_url = f"{self.BASE_URL}/?q={url}&followRedirects=on"
        self.session.headers["Referer"] = self.BASE_URL + "/"

        response = self.session.get(check_url, timeout=30)
        response.raise_for_status()

        return self._parse_response(url, response.text)

    def _parse_response(self, url: str, html: str) -> Dict:
        """Parse the SecurityHeaders.com response"""
        soup = BeautifulSoup(html, "lxml")

        result = {
            "url": url,
            "score": None,
            "grade": None,
            "headers": [],
            "checked_at": datetime.utcnow().isoformat()
        }

        # Find grade
        grade_elem = soup.find("span", class_="grade")
        if grade_elem:
            result["grade"] = grade_elem.get_text(strip=True)

        # Find score
        score_elem = soup.find("div", class_="score")
        if score_elem:
            score_text = score_elem.get_text(strip=True)
            match = re.search(r"(\d+)", score_text)
            if match:
                result["score"] = int(match.group(1))

        # Find headers table
        headers_section = soup.find("section", id="headers")
        if headers_section:
            rows = headers_section.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    header_name = cols[0].get_text(strip=True)
                    header_value = cols[1].get_text(strip=True)
                    rating_elem = cols[0].find("span", class_=re.compile("rating"))
                    rating = "good"
                    if rating_elem:
                        rating_class = rating_elem.get("class", [])
                        if "warning" in rating_class:
                            rating = "warning"
                        elif "bad" in rating_class:
                            rating = "bad"

                    result["headers"].append({
                        "name": header_name,
                        "value": header_value,
                        "rating": rating
                    })

        # If no grade found, try to find it in other elements
        if not result["grade"]:
            # Try finding any element with grade
            for elem in soup.find_all(class_=re.compile("grade")):
                text = elem.get_text(strip=True)
                if text in ["A", "B", "C", "D", "F"]:
                    result["grade"] = text
                    break

        result["grade"] = self.normalize_grade(result.get("grade"))
        return result

    def check_batch(self, urls: List[str], progress_callback=None) -> List[Dict]:
        """Check multiple URLs with optional progress callback"""
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            result = self.check_url(url)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total)

        return results


# Singleton instance
_ranking_service = None


def get_ranking_service() -> RankingService:
    """Get singleton instance of RankingService"""
    global _ranking_service
    if _ranking_service is None:
        _ranking_service = RankingService()
    return _ranking_service
