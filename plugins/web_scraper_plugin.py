"""
Web scraper plugin providing advanced web content extraction capabilities.
"""
import time
import re
import json
from typing import Dict, List, Any, Optional, Union

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

# --- Dependency Check ---
_SELENIUM_AVAILABLE = False
_BS4_AVAILABLE = False
_REQUESTS_AVAILABLE = False
_PANDAS_AVAILABLE = False

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    pass

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    pass

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    _SELENIUM_AVAILABLE = True
except ImportError:
    pass

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    pass
# --- End Dependency Check ---


class WebScraperPlugin(Plugin):
    """Plugin providing advanced web scraping operations."""

    @staticmethod
    @tool(
        categories=["web"],
        requires_network=True,
        rate_limited=True,
        description="Advanced tool to fetch and extract content from a URL with various modes.",
        params={
            "url": {"type": str, "required": True, "description": "URL of the webpage."},
            "mode": {
                "type": str,
                "required": False,
                "default": "smart",
                "enum": ["smart", "text", "structured", "dynamic", "tables"],
                "description": "Extraction mode: 'smart' (clean main content), 'text' (full raw text), 'structured' (CSS selectors), 'dynamic' (JS rendering), 'tables' (HTML tables)."
            },
            "render_js": {"type": bool, "required": False, "default": False, "description": "Set to true for sites needing JavaScript rendering (implies using Selenium). 'dynamic' mode automatically sets this."},
            "wait_time": {"type": int, "required": False, "default": 5, "description": "Wait time in seconds for JS execution if render_js is true."},
            "selectors": {"type": dict, "required": False, "description": "Dict mapping field names to CSS selectors (required for 'structured' mode). E.g. {'title': 'h1', 'price': '.price'}"},
            "table_index": {"type": int, "required": False, "default": -1, "description": "Index of table to extract for 'tables' mode (-1 for all tables)."},
            "pagination_config": {"type": dict, "required": False, "description": "Configuration for pagination: {'page_param': 'page', 'max_pages': 3, 'start_page': 1, 'content_selector': 'body'}"}
        }
    )
    def advanced_web_scrape(
        url: str,
        mode: str = "smart",
        render_js: bool = False,
        wait_time: int = 5,
        selectors: Optional[Dict[str, str]] = None,
        table_index: int = -1,
        pagination_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetches and extracts content from a URL using various modes and options.

        Args:
            url: URL of the webpage.
            mode: Extraction mode ('smart', 'text', 'structured', 'dynamic', 'tables').
            render_js: Whether to render JavaScript (uses Selenium). 'dynamic' mode forces this.
            wait_time: Seconds to wait for JS rendering.
            selectors: CSS selectors for 'structured' mode.
            table_index: Index for 'tables' mode (-1 for all).
            pagination_config: Dict with pagination settings if needed.

        Returns:
            Dictionary containing the extracted data based on the mode.

        Raises:
            PluginError: If dependencies are missing or errors occur during scraping.
        """
        tool_message_print(f"Advanced web scrape started for: {url} (Mode: {mode})")

        # --- Dependency Checks ---
        if not _REQUESTS_AVAILABLE:
            raise PluginError("requests library is required.", plugin_name="WebScraperPlugin")
        if not _BS4_AVAILABLE:
             raise PluginError("beautifulsoup4 library is required.", plugin_name="WebScraperPlugin")
        if (render_js or mode == "dynamic") and not _SELENIUM_AVAILABLE:
             raise PluginError("selenium library is required for JavaScript rendering.", plugin_name="WebScraperPlugin")
        if mode == "tables" and not _PANDAS_AVAILABLE:
             raise PluginError("pandas library is required for table extraction.", plugin_name="WebScraperPlugin")

        # --- Parameter Validation ---
        if mode == "structured" and not selectors:
            raise PluginError("Selectors must be provided for 'structured' mode.", plugin_name="WebScraperPlugin")
        if mode == "dynamic":
            render_js = True # Force JS rendering for dynamic mode

        # --- Main Logic ---
        try:
            # Handle Pagination Separately if configured
            if pagination_config:
                return WebScraperPlugin._scrape_paginated(url, pagination_config)

            # Handle Dynamic/JS Rendering
            elif render_js:
                 return WebScraperPlugin._scrape_dynamic(url, wait_time, selectors if mode == 'structured' else ['body'])

            # Handle Static Content Modes
            else:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                html_content = response.text

                if mode == "text":
                    return {"url": url, "mode": mode, "content": html_content, "content_length": len(html_content)}
                elif mode == "smart":
                    return WebScraperPlugin._extract_smart_content(url, html_content)
                elif mode == "structured":
                    return WebScraperPlugin._extract_structured_static(url, html_content, selectors)
                elif mode == "tables":
                    return WebScraperPlugin._extract_tables_static(url, html_content, table_index)
                else:
                    raise PluginError(f"Invalid mode specified: {mode}", plugin_name="WebScraperPlugin")

        except Exception as e:
            # Catch potential requests/bs4/selenium/pandas errors
            if isinstance(e, PluginError): # Don't wrap PluginErrors
                raise e
            raise PluginError(f"Error during advanced web scrape: {e}", plugin_name="WebScraperPlugin") from e

    # --- Helper methods extracted from original tools ---

    @staticmethod
    def _extract_smart_content(url: str, html_content: str) -> Dict[str, Any]:
        """Helper for smart content extraction."""
        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'form']):
            element.decompose()

        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else "No title found"

        metadata = {}
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '')
            name = meta.get('name', '')
            if prop.startswith('og:'):
                metadata[prop] = meta.get('content', '')
            elif name == 'description':
                metadata['description'] = meta.get('content', '')

        ad_classes = ['ad', 'ads', 'advertisement', 'banner', 'sidebar', 'social', 'share', 'comment', 'comments', 'footer']
        for class_name in ad_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.IGNORECASE)):
                element.decompose()

        main_content_element = None
        potential_tags = ['article', 'main']
        potential_classes = ['content', 'main', 'article', 'post', 'body', 'entry', 'text']
        for tag in potential_tags:
             main_content_element = soup.find(tag)
             if main_content_element: break
        if not main_content_element:
             for class_name in potential_classes:
                 main_content_element = soup.find('div', class_=class_name)
                 if main_content_element: break
        if not main_content_element:
            main_content_element = soup.body

        if not main_content_element:
             raise PluginError("Could not identify main content area.", plugin_name="WebScraperPlugin")

        paragraphs = []
        for p in main_content_element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
             text = p.get_text(strip=True)
             # Basic filtering for meaningful text
             if text and len(text.split()) > 3:
                 paragraphs.append(text)

        if not paragraphs:
            # Fallback: get all text if paragraph extraction fails
            paragraphs = [main_content_element.get_text(separator='\n', strip=True)]
            if not paragraphs or not paragraphs[0]:
                 raise PluginError("No significant text content found.", plugin_name="WebScraperPlugin")

        content = '\n\n'.join(paragraphs)
        result = {
            "url": url,
            "mode": "smart",
            "title": title_text,
            "metadata": metadata,
            "content": content,
            "content_length": len(content),
            "paragraph_count": len(paragraphs),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        tool_report_print(f"Smart extraction: {len(paragraphs)} paragraphs ({len(content)} chars)")
        return result

    @staticmethod
    def _extract_structured_static(url: str, html_content: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Helper for structured data extraction from static HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        result_data = {}
        for field, selector in selectors.items():
            elements = soup.select(selector)
            if elements:
                if len(elements) > 1:
                    result_data[field] = [el.get_text(strip=True) for el in elements]
                else:
                    result_data[field] = elements[0].get_text(strip=True)
            else:
                result_data[field] = None

        result = {
            "url": url,
            "mode": "structured",
            "data": result_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data_count = sum(1 for v in result_data.values() if v is not None and v != [])
        tool_report_print(f"Structured extraction: {data_count} fields matched")
        return result

    @staticmethod
    def _extract_tables_static(url: str, html_content: str, table_index: int) -> Dict[str, Any]:
        """Helper for table extraction from static HTML."""
        tables = pd.read_html(html_content)
        if not tables:
            raise PluginError("No tables found on the page", plugin_name="WebScraperPlugin")

        tables_data = []
        table_count_extracted = 0
        if table_index >= 0 and table_index < len(tables):
            df = tables[table_index]
            tables_data.append({
                "index": table_index, "shape": df.shape, "columns": list(df.columns),
                "data": df.to_dict(orient='records')
            })
            table_count_extracted = 1
        elif table_index == -1:
            for i, df in enumerate(tables):
                tables_data.append({
                    "index": i, "shape": df.shape, "columns": list(df.columns),
                    "data": df.to_dict(orient='records')
                })
            table_count_extracted = len(tables)
        else:
            raise PluginError(f"Table index {table_index} out of range (0-{len(tables)-1})", plugin_name="WebScraperPlugin")

        result = {
            "url": url, "mode": "tables", "total_tables_found": len(tables),
            "tables_extracted_count": table_count_extracted, "tables": tables_data
        }
        total_rows = sum(t["shape"][0] for t in tables_data)
        tool_report_print(f"Table extraction: Extracted {table_count_extracted} tables, {total_rows} total rows")
        return result

    @staticmethod
    def _scrape_dynamic(url: str, wait_time: int, selectors: List[str]) -> Dict[str, Any]:
        """Helper for dynamic content scraping using Selenium."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Add a common user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")


        results = {"url": url, "mode": "dynamic", "content": {}}
        page_source = ""

        with webdriver.Chrome(options=options) as driver:
            driver.set_page_load_timeout(30) # Increased timeout
            driver.get(url)
            tool_message_print(f"Waiting {wait_time}s for JS execution...")
            time.sleep(wait_time) # Simple wait

            page_source = driver.page_source # Get source after JS runs

            # If selectors provided, extract specific elements
            if selectors and selectors != ['body']:
                 for selector in selectors:
                     try:
                         # Wait slightly for element presence after initial JS load
                         element = WebDriverWait(driver, 10).until(
                             EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                         )
                         # Try getting text, fallback to outerHTML
                         content_text = element.text or element.get_attribute('outerHTML')
                         results["content"][selector] = content_text.strip() if content_text else None
                     except TimeoutException:
                         results["content"][selector] = None
                         tool_message_print(f"Warning: Selector '{selector}' not found after wait.")
            else:
                 # Default: Get the text of the whole body if no specific selectors
                 try:
                      body_element = WebDriverWait(driver, 10).until(
                          EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
                      )
                      results["content"]["body"] = body_element.text.strip()
                 except TimeoutException:
                      results["content"]["body"] = None
                      tool_message_print("Warning: Body element not found after wait.")


        results["page_source_length"] = len(page_source)
        selector_count = sum(1 for s, v in results["content"].items() if v is not None)
        tool_report_print(f"Dynamic scrape: Extracted {selector_count} elements/body")
        return results

    @staticmethod
    def _scrape_paginated(base_url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Helper for scraping paginated content."""
        max_pages = config.get('max_pages', 3)
        page_param = config.get('page_param', 'page')
        start_page = config.get('start_page', 1)
        content_selector = config.get('content_selector', 'body')

        results = {"base_url": base_url, "mode": "pagination", "pages": []}
        url_format = f"{base_url}{'&' if '?' in base_url else '?'}{page_param}={{}}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}

        for page_num in range(start_page, start_page + max_pages):
            page_url = url_format.format(page_num)
            tool_message_print(f"Scraping page {page_num}: {page_url}")
            try:
                response = requests.get(page_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                content_elements = soup.select(content_selector)

                if not content_elements:
                    tool_message_print(f"Warning: No content found with selector '{content_selector}' on page {page_num}")
                    page_content = "" # Continue pagination even if one page fails
                else:
                    # Join text from potentially multiple matching elements
                    page_content = "\n\n".join(element.get_text(strip=True) for element in content_elements)

                results["pages"].append({
                    "url": page_url,
                    "page_number": page_num,
                    "content_preview": page_content[:500] + ("..." if len(page_content) > 500 else ""),
                    "content_length": len(page_content),
                    "status": "success"
                })
            except requests.exceptions.RequestException as e:
                 tool_message_print(f"Error fetching page {page_num}: {e}")
                 results["pages"].append({
                     "url": page_url,
                     "page_number": page_num,
                     "status": "error",
                     "error_message": str(e)
                 })
                 # Optional: Stop pagination on first error? For now, continue.
            except Exception as e:
                 tool_message_print(f"Error processing page {page_num}: {e}")
                 results["pages"].append({
                     "url": page_url,
                     "page_number": page_num,
                     "status": "error",
                     "error_message": str(e)
                 })

            time.sleep(0.5) # Small delay between pages

        tool_report_print(f"Pagination scrape: Processed {len(results['pages'])} pages.")
        return results

# Keep the class definition
# The original tool methods (@tool decorated staticmethods) are now removed
# and replaced by the single advanced_web_scrape tool and its helpers.
