"""Service for scanning security headers using Playwright."""
import asyncio
import base64
from typing import Dict, Any, Optional
from pyppeteer import launch

async def security_scan(website_url: str, capture_screenshot: bool = False) -> Dict[str, Any]:
    """Scan securityheaders.com using Playwright/Pyppeteer."""
    if not website_url:
        return {"success": False, "error": "No website URL provided"}
        
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"

    browser = await launch(headless=True, args=['--no-sandbox'])
    try:
        page = await browser.newPage()
        # Set viewport to ensure screenshot captures the top area nicely
        await page.setViewport({"width": 1280, "height": 800})
        
        target_url = f"https://securityheaders.com/?q={website_url}"
        await page.goto(target_url, waitUntil='domcontentloaded', timeout=60000)
        
        # Wait a bit longer as securityheaders.com sometimes uses Cloudflare or takes time to process
        await asyncio.sleep(12)
        
        try:
            grade_element_handle = await page.querySelector('.grade')
            if grade_element_handle:
                grade = await page.evaluate('(el) => el.textContent', grade_element_handle)
                grade = grade.strip()
            else:
                grade = "N/A"
        except Exception:
            grade = "Error"
            
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
