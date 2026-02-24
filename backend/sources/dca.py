"""
California DCA License Search Client

Handles lookups against the CA DCA License Search via Playwright scraping.
In mock mode, returns synthetic data from dca_mock_data.py.

Real DCA URL: https://search.dca.ca.gov/?BD=800
"""

import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import MOCK_MODE, MAX_RETRIES, BASE_RETRY_DELAY
from sources.dca_mock_data import get_mock_dca_response, DCASourceUnavailableError


class SourceUnavailableError(Exception):
    """Raised when a source is unavailable after all retries."""
    pass


@dataclass
class DCALookupResult:
    """Result of a DCA license lookup."""

    # Raw response
    raw_response: Optional[Dict[str, Any]] = None

    # Parsed fields
    license_found: bool = False
    license_number: Optional[str] = None
    license_status: Optional[str] = None  # "Current/Active", "License Revoked", etc.
    license_type: Optional[str] = None
    expiration_date: Optional[str] = None
    secondary_status: Optional[str] = None
    name_on_license: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    zip_code: Optional[str] = None
    detail_url: Optional[str] = None
    has_disciplinary_action: bool = False
    has_public_documents: bool = False

    # Source availability
    source_available: bool = True
    error_message: Optional[str] = None

    # Metrics
    latency_ms: int = 0
    retry_count: int = 0


async def lookup_dca_license(
    license_number: str,
    target_state: str = "CA"
) -> DCALookupResult:
    """
    Look up a license in the CA DCA database.

    In mock mode, returns data from dca_mock_data.py.
    In live mode, uses Playwright to scrape the DCA search page.

    Args:
        license_number: The CA license number (e.g., "A128437")
        target_state: Target state (unused, always CA for this module)

    Returns:
        DCALookupResult with license data
    """
    start_time = time.time()
    result = DCALookupResult()

    if MOCK_MODE:
        # Use mock data
        result = await _mock_lookup(license_number)
    else:
        # Use real Playwright scraping
        result = await _playwright_lookup(license_number)

    result.latency_ms = int((time.time() - start_time) * 1000)
    return result


async def _mock_lookup(license_number: str) -> DCALookupResult:
    """
    Look up license in mock data.

    Args:
        license_number: The CA license number

    Returns:
        DCALookupResult
    """
    result = DCALookupResult()

    try:
        mock_data = get_mock_dca_response(license_number)

        if mock_data is None:
            # License not found in mock data
            result.license_found = False
            result.source_available = True
            return result

        # Parse mock data
        result.license_found = True
        result.source_available = True
        result.raw_response = mock_data
        result.license_number = mock_data.get("license_number")
        result.license_status = mock_data.get("license_status")
        result.license_type = mock_data.get("license_type")
        result.expiration_date = mock_data.get("expiration_date")
        result.secondary_status = mock_data.get("secondary_status")
        result.name_on_license = mock_data.get("name")
        result.city = mock_data.get("city")
        result.state = mock_data.get("state")
        result.county = mock_data.get("county")
        result.zip_code = mock_data.get("zip")
        result.detail_url = mock_data.get("detail_url")
        result.has_disciplinary_action = mock_data.get("has_disciplinary_action", False)
        result.has_public_documents = mock_data.get("has_public_documents", False)

    except DCASourceUnavailableError as e:
        # Mock simulates CAPTCHA failure
        result.license_found = False
        result.source_available = False
        result.error_message = str(e)

    return result


async def _playwright_lookup(license_number: str) -> DCALookupResult:
    """
    Look up license using Playwright to scrape DCA.

    This function includes retry logic with fresh browser contexts.

    Args:
        license_number: The CA license number

    Returns:
        DCALookupResult
    """
    result = DCALookupResult()
    retry_count = 0

    for attempt in range(MAX_RETRIES + 1):
        try:
            # Import playwright here to avoid dependency issues in mock mode
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Launch browser - try headless first
                browser = await p.chromium.launch(headless=True)

                try:
                    context = await browser.new_context()
                    page = await context.new_page()

                    # Navigate to DCA search
                    await page.goto("https://search.dca.ca.gov/?BD=800", timeout=30000)

                    # Wait for the form to load
                    await page.wait_for_selector("#licenseNumber", timeout=10000)

                    # Select Medical Board of California
                    await page.select_option("#boardCode", "16")

                    # Select Physician's and Surgeon's license type
                    await page.select_option("#licenseType", "289")

                    # Fill in license number
                    await page.fill("#licenseNumber", license_number)

                    # Wait for Turnstile CAPTCHA to auto-solve (if present)
                    # This may not work if Turnstile detects automation
                    await asyncio.sleep(2)  # Brief wait for Turnstile

                    # Click search
                    await page.click("#srchSubmitHome")

                    # Wait for results
                    try:
                        await page.wait_for_selector("article.post", timeout=10000)
                    except Exception:
                        # No results found
                        result.license_found = False
                        result.source_available = True
                        return result

                    # Parse the first result
                    article = await page.query_selector("article.post")
                    if article:
                        result = await _parse_dca_result(page, article)

                    await browser.close()
                    return result

                except Exception as e:
                    await browser.close()
                    raise e

        except Exception as e:
            if attempt < MAX_RETRIES:
                retry_count += 1
                delay = BASE_RETRY_DELAY * (2 ** attempt)  # 2s, 4s, 8s
                print(f"DCA scraper error: {e}. Retry {attempt + 1}/{MAX_RETRIES} in {delay}s")
                await asyncio.sleep(delay)
                continue
            else:
                # All retries exhausted
                result.license_found = False
                result.source_available = False
                result.error_message = f"DCA source unavailable: {str(e)}"
                result.retry_count = retry_count
                return result

    return result


async def _parse_dca_result(page, article) -> DCALookupResult:
    """
    Parse a DCA search result article element.

    Args:
        page: Playwright page object
        article: The article element containing the result

    Returns:
        DCALookupResult with parsed data
    """
    result = DCALookupResult()
    result.license_found = True
    result.source_available = True

    try:
        # Extract name from footer
        name_el = await article.query_selector("footer ul.actions li h3")
        if name_el:
            result.name_on_license = await name_el.text_content()

        # Extract license number from link
        lic_link = await article.query_selector("a[href*='/details/']")
        if lic_link:
            lic_span = await lic_link.query_selector("span[id^='lic']")
            if lic_span:
                result.license_number = await lic_span.text_content()

            # Get detail URL
            result.detail_url = await lic_link.get_attribute("href")

        # Get full text content for parsing
        text_content = await article.text_content()

        # Parse text content for fields
        lines = [line.strip() for line in text_content.split("\n") if line.strip()]

        for i, line in enumerate(lines):
            if "License Type:" in line:
                result.license_type = line.replace("License Type:", "").strip()
            elif "License Status:" in line:
                result.license_status = line.replace("License Status:", "").strip()
            elif "Expiration Date:" in line:
                result.expiration_date = line.replace("Expiration Date:", "").strip()
            elif "Secondary Status:" in line:
                result.secondary_status = line.replace("Secondary Status:", "").strip()

        # Check for disciplinary action icon
        disc_icon = await article.query_selector("img[alt*='disciplinary action']")
        result.has_disciplinary_action = disc_icon is not None

        # Check for public documents icon
        docs_icon = await article.query_selector("img[alt*='public documents']")
        result.has_public_documents = docs_icon is not None

        # Extract city from span
        city_span = await article.query_selector("span[id^='city']")
        if city_span:
            result.city = await city_span.text_content()

        # Build raw response
        result.raw_response = {
            "name": result.name_on_license,
            "license_number": result.license_number,
            "license_type": result.license_type,
            "license_status": result.license_status,
            "expiration_date": result.expiration_date,
            "secondary_status": result.secondary_status,
            "city": result.city,
            "has_disciplinary_action": result.has_disciplinary_action,
            "has_public_documents": result.has_public_documents,
            "detail_url": result.detail_url,
        }

    except Exception as e:
        print(f"Error parsing DCA result: {e}")
        result.error_message = str(e)

    return result
