"""Service for scanning security headers using Playwright."""
import asyncio
import base64
from typing import Dict, Any, Optional

from services.ranking_service import get_ranking_service

async def security_scan(website_url: str, capture_screenshot: bool = False) -> Dict[str, Any]:
    """Scan website security data.

    - Non-screenshot mode: uses RankingService (Railway-safe, no browser dependency).
    - Screenshot mode: tries Playwright and falls back with a clear error when unavailable.
    """
    if not website_url:
        return {"success": False, "error": "No website URL provided"}
        
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"

    if not capture_screenshot:
        try:
            svc = get_ranking_service()
            result = svc.check_url(website_url)
            return {
                "success": True,
                "grade": result.get("grade"),
                "url": result.get("url") or website_url,
                "score": result.get("score"),
                "headers": result.get("headers") or [],
                "screenshot_b64": None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {
            "success": False,
            "error": "Playwright/Chromium not available on this environment",
        }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            # Set viewport to ensure screenshot captures the top area nicely
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            target_url = f"https://securityheaders.com/?q={website_url}"
            # securityheaders.com can be slow or use Cloudflare
            await page.goto(target_url, timeout=60000)
            
            await page.wait_for_timeout(8000)
            
            try:
                grade_element_handle = await page.query_selector('.grade')
                if grade_element_handle:
                    grade = await grade_element_handle.text_content()
                    grade = grade.strip()
                else:
                    grade = None
            except Exception:
                grade = None
                
            screenshot_b64 = None
            if capture_screenshot:
                try:
                    # Capture the top of the page (where the grade is)
                    screenshot_bytes = await page.screenshot(clip={"x": 0, "y": 0, "width": 800, "height": 600})
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                except Exception as e:
                    print(f"Screenshot failed: {e}")

            return {
                "success": True,
                "grade": grade,
                "url": target_url,
                "screenshot_b64": screenshot_b64
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()
