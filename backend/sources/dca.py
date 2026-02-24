"""
California DCA License Search Client

Handles lookups against the CA DCA License Search via Playwright scraping.
In mock mode, returns synthetic data from dca_mock_data.py.

Real DCA URL: https://search.dca.ca.gov/?BD=800
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import MOCK_MODE, BASE_RETRY_DELAY, DCA_HEADED, DCA_CHROME_USER_DATA_DIR, DCA_MAX_RETRIES

logger = logging.getLogger(__name__)
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
        logger.info("DCA: Mock lookup for license=%s", license_number)
        result = await _mock_lookup(license_number)
    else:
        # Use real Playwright scraping
        result = await _playwright_lookup(license_number)

    result.latency_ms = int((time.time() - start_time) * 1000)
    logger.info("DCA: Completed: license=%s found=%s status=%s latency=%dms",
                 license_number, result.license_found, result.license_status, result.latency_ms)
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
            logger.info("DCA: Mock data not found for license=%s", license_number)
            result.license_found = False
            result.source_available = True
            return result

        # Parse mock data
        logger.info("DCA: Mock data found for license=%s status=%s",
                     license_number, mock_data.get("license_status"))
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

    for attempt in range(DCA_MAX_RETRIES + 1):
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import Stealth

            stealth = Stealth()
            async with stealth.use_async(async_playwright()) as p:
                to_close = None
                if DCA_CHROME_USER_DATA_DIR:
                    user_data = str(Path(DCA_CHROME_USER_DATA_DIR).expanduser())
                    try:
                        logger.info(
                            "DCA: Launching Chrome with persistent context (headed=%s, profile=%s)",
                            DCA_HEADED,
                            user_data,
                        )
                        context = await p.chromium.launch_persistent_context(
                            user_data,
                            headless=not DCA_HEADED,
                            channel="chrome",
                            args=["--disable-blink-features=AutomationControlled"],
                            ignore_default_args=["--enable-automation"],
                        )
                        page = await context.new_page()
                        to_close = context
                    except Exception as profile_err:
                        if "profile is already in use" in str(profile_err) or "ProcessSingleton" in str(profile_err):
                            logger.warning(
                                "DCA: Chrome profile in use, falling back to Chromium. Close Chrome to use your profile."
                            )
                        else:
                            raise
                if to_close is None:
                    logger.info("DCA: Launching Chromium (headed=%s)", DCA_HEADED)
                    browser = await p.chromium.launch(
                        headless=not DCA_HEADED,
                        args=["--disable-blink-features=AutomationControlled"],
                        ignore_default_args=["--enable-automation"],
                    )
                    context = await browser.new_context()
                    page = await context.new_page()
                    to_close = browser

                try:
                    logger.info("DCA: Navigating to search.dca.ca.gov")
                    await page.goto("https://search.dca.ca.gov/?BD=800", timeout=30000)

                    logger.info("DCA: Waiting for form")
                    await page.wait_for_selector("#licenseNumber", timeout=10000)

                    logger.info("DCA: Selecting board=16, licenseType=289")
                    await page.select_option("#boardCode", "16")
                    await page.select_option("#licenseType", "289")

                    logger.info("DCA: Filling license=%s", license_number)
                    await page.fill("#licenseNumber", license_number)

                    submit_btn = await page.query_selector("#srchSubmitHome")
                    if submit_btn:
                        disabled = await submit_btn.get_attribute("disabled")
                        logger.info("DCA: Submit button state before wait: disabled=%s", disabled)

                    logger.info("DCA: Waiting for Turnstile/CAPTCHA (max 30s)")
                    try:
                        await page.wait_for_selector("#srchSubmitHome:not([disabled])", timeout=30000)
                    except Exception as wait_err:
                        disabled = await page.evaluate(
                            "() => document.querySelector('#srchSubmitHome')?.disabled ?? true"
                        )
                        logger.warning(
                            "DCA: Submit button still disabled=%s after 30s. Turnstile may be blocking. %s",
                            disabled,
                            wait_err,
                        )
                        raise

                    logger.info("DCA: Clicking search")
                    await page.click("#srchSubmitHome")

                    logger.info("DCA: Waiting for results")
                    try:
                        await page.wait_for_selector("article.post", timeout=10000)
                    except Exception as e:
                        logger.info("DCA: No results found or timeout: %s", e)
                        result.license_found = False
                        result.source_available = True
                        return result

                    articles = await page.query_selector_all("article.post")
                    logger.info("DCA: Found %d result(s) for license=%s", len(articles), license_number)

                    article = None
                    if len(articles) == 1:
                        article = articles[0]
                    elif len(articles) > 1:
                        # Multiple results — match by exact license number
                        normalized_input = license_number.replace(" ", "").upper()
                        for candidate in articles:
                            lic_span = await candidate.query_selector("span[id^='lic']")
                            if lic_span:
                                lic_text = (await lic_span.text_content() or "").replace(" ", "").upper()
                                if lic_text == normalized_input:
                                    logger.info("DCA: Exact match found: %s", lic_text)
                                    article = candidate
                                    break
                        if article is None:
                            logger.warning(
                                "DCA: No exact license match for %s among %d results, falling back to first",
                                license_number, len(articles),
                            )
                            article = articles[0]

                    if article:
                        result = await _parse_dca_result(page, article)

                    await to_close.close()
                    return result

                except Exception as e:
                    await to_close.close()
                    raise e

        except Exception as e:
            logger.warning("DCA: Attempt %s failed: %s", attempt + 1, e)
            if attempt < DCA_MAX_RETRIES:
                retry_count += 1
                delay = BASE_RETRY_DELAY * (2 ** attempt)
                logger.info("DCA: Retry %s/%s in %ss", attempt + 1, DCA_MAX_RETRIES, delay)
                logger.warning("DCA: Scraper error: %s. Retry %d/%d in %ss", e, attempt + 1, DCA_MAX_RETRIES, delay)
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

        # Check for disciplinary action icon (parent <a> is display:none when no action)
        disc_link = await article.query_selector("a.iconLink[href$='#pr']")
        if disc_link:
            result.has_disciplinary_action = await disc_link.is_visible()
        else:
            result.has_disciplinary_action = False

        # Check for public documents link
        docs_link = await article.query_selector("a.iconLink:not([href$='#pr'])")
        if docs_link:
            result.has_public_documents = await docs_link.is_visible()
        else:
            result.has_public_documents = False

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
        logger.error("DCA: Error parsing result: %s", e, exc_info=True)
        result.error_message = str(e)

    return result
