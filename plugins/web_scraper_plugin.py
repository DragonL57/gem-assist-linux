"""
Web scraper plugin providing advanced web content extraction capabilities.
"""
import time
import re
from typing import Dict, List, Any, Optional, Union

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

class WebScraperPlugin(Plugin):
    """Plugin providing web scraping operations."""
    
    @staticmethod
    @tool(
        categories=["web", "scraping"],
        requires_network=True,
        rate_limited=True
    )
    def extract_structured_data(
        url: str, 
        selectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract structured data from a webpage using CSS selectors.
        
        Args:
            url: URL of the webpage to scrape
            selectors: Dictionary mapping field names to CSS selectors (e.g. {"title": "h1.main-title", "price": "span.price"})
            
        Returns:
            Dictionary with extracted data
        """
        tool_message_print(f"Extracting structured data from: {url}")
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Make the request with a reasonable timeout
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data based on selectors
            result = {}
            for field, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    # If multiple elements found, get all text contents
                    if len(elements) > 1:
                        result[field] = [el.get_text(strip=True) for el in elements]
                    # If single element, get text content
                    else:
                        result[field] = elements[0].get_text(strip=True)
                else:
                    result[field] = None
                    
            # Add metadata
            result["url"] = url
            result["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Print summary
            data_count = sum(1 for v in result.values() if v is not None and v != [])
            tool_report_print(f"Extracted {data_count} data fields from {url}")
            
            return result
            
        except Exception as e:
            raise PluginError(f"Error extracting structured data: {e}", plugin_name=WebScraperPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "data"],
        requires_network=True,
        rate_limited=True
    )
    def extract_tables_to_dataframes(url: str, table_index: int = 0) -> Dict[str, Any]:
        """
        Extract HTML tables from a webpage into pandas DataFrames.
        
        Args:
            url: URL of the webpage containing tables
            table_index: Index of the specific table to extract (-1 for all tables)
            
        Returns:
            Dictionary with table data and metadata
        """
        tool_message_print(f"Extracting tables from: {url}")
        
        try:
            import requests
            import pandas as pd
            
            # Make the request
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Read HTML tables
            tables = pd.read_html(response.text)
            
            if not tables:
                raise PluginError("No tables found on the page", plugin_name=WebScraperPlugin.__name__)
                
            # Process tables based on index
            if table_index >= 0 and table_index < len(tables):
                # Extract specific table
                df = tables[table_index]
                tables_data = [{
                    "index": table_index,
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "data": df.to_dict(orient='records')
                }]
                table_count = 1
            elif table_index == -1:
                # Extract all tables
                tables_data = []
                for i, df in enumerate(tables):
                    tables_data.append({
                        "index": i,
                        "shape": df.shape,
                        "columns": list(df.columns),
                        "data": df.to_dict(orient='records')
                    })
                table_count = len(tables)
            else:
                raise PluginError(
                    f"Table index {table_index} out of range (0-{len(tables)-1})", 
                    plugin_name=WebScraperPlugin.__name__
                )
            
            # Build result
            result = {
                "url": url,
                "table_count": table_count,
                "tables": tables_data
            }
            
            # Print summary
            total_rows = sum(t["shape"][0] for t in tables_data)
            tool_report_print(f"Extracted {table_count} tables with {total_rows} total rows from {url}")
            
            return result
            
        except Exception as e:
            raise PluginError(f"Error extracting tables: {e}", plugin_name=WebScraperPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "scraping"],
        requires_network=True,
        rate_limited=True
    )
    def scrape_with_pagination(
        base_url: str, 
        max_pages: int = 3, 
        page_param: str = "page", 
        start_page: int = 1, 
        content_selector: str = "body"
    ) -> Dict[str, Any]:
        """
        Scrape content from multiple pages of a paginated website.
        
        Args:
            base_url: Base URL for the paginated content
            max_pages: Maximum number of pages to scrape
            page_param: URL parameter name for the page number
            start_page: Page number to start scraping from
            content_selector: CSS selector for the main content
            
        Returns:
            Dictionary with content from all pages
        """
        tool_message_print(f"Scraping paginated content from: {base_url}")
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            results = {
                "base_url": base_url,
                "pages": []
            }
            
            # Determine URL format
            if "?" in base_url:
                url_format = base_url + f"&{page_param}={{}}"
            else:
                url_format = base_url + f"?{page_param}={{}}"
            
            # Process each page
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
            
            for page_num in range(start_page, start_page + max_pages):
                # Format the page URL
                page_url = url_format.format(page_num)
                
                # Make the request
                response = requests.get(page_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Parse the content
                soup = BeautifulSoup(response.text, 'html.parser')
                content = soup.select(content_selector)
                
                if not content:
                    raise PluginError(
                        f"No content found with selector '{content_selector}' on page {page_num}",
                        plugin_name=WebScraperPlugin.__name__
                    )
                
                # Extract text content
                text_content = " ".join(element.get_text(strip=True) for element in content)
                
                # Add to results
                results["pages"].append({
                    "url": page_url,
                    "page_number": page_num,
                    "content": text_content[:1000] + ("..." if len(text_content) > 1000 else "")
                })
                
                # Add a short delay to avoid overloading the server
                time.sleep(1)
                
            # Print summary
            tool_report_print(f"Scraped {len(results['pages'])} pages from {base_url}")
            
            return results
            
        except Exception as e:
            raise PluginError(f"Error scraping paginated content: {e}", plugin_name=WebScraperPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "scraping"],
        requires_network=True,
        rate_limited=True
    )
    def scrape_dynamic_content(url: str, wait_time: int = 5, selectors: List[str] = None) -> Dict[str, Any]:
        """
        Scrape content from a JavaScript-heavy website that requires browser rendering.
        
        Args:
            url: URL to scrape
            wait_time: Time to wait for JavaScript execution (seconds)
            selectors: List of CSS selectors to extract (default: body)
            
        Returns:
            Dictionary with scraped content
        """
        tool_message_print(f"Scraping dynamic content from: {url}")
        
        try:
            # Check if Selenium is available
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.common.exceptions import TimeoutException
            except ImportError:
                raise PluginError(
                    "Selenium is not installed. Install with 'pip install selenium'",
                    plugin_name=WebScraperPlugin.__name__
                )
                
            # Set default selectors if none provided
            if selectors is None:
                selectors = ["body"]
                
            # Configure Chrome options
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Initialize the driver and extract content
            results = {"url": url, "content": {}}
            
            with webdriver.Chrome(options=options) as driver:
                # Set page load timeout
                driver.set_page_load_timeout(30)
                
                # Navigate to the URL
                driver.get(url)
                
                # Wait for the specified time to let JavaScript execute
                time.sleep(wait_time)
                
                # Extract content for each selector
                for selector in selectors:
                    try:
                        # Try to wait for the element to be present
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        
                        # Get the text content
                        content = element.text
                        results["content"][selector] = content
                        
                    except TimeoutException:
                        results["content"][selector] = None
                        
                # Get page source
                results["page_source_length"] = len(driver.page_source)
            
            # Print summary
            selector_count = len([s for s in results["content"] if results["content"][s] is not None])
            tool_report_print(f"Extracted {selector_count} dynamic elements from {url}")
            
            return results
                
        except Exception as e:
            raise PluginError(f"Error scraping dynamic content: {e}", plugin_name=WebScraperPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "content"],
        requires_network=True,
        rate_limited=True
    )
    def smart_content_extraction(url: str) -> Dict[str, Any]:
        """
        Intelligently extract clean, readable content from a webpage with metadata.
        
        Args:
            url: URL of the webpage to extract content from
            
        Returns:
            Dictionary with extracted content and metadata
        """
        tool_message_print(f"Extracting smart content from: {url}")
        
        try:
            import requests
            import re
            from bs4 import BeautifulSoup
            
            # Make the request
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'form']):
                element.decompose()
                
            # Extract title
            title = soup.find('title')
            title_text = title.get_text() if title else "No title found"
            
            # Extract metadata
            metadata = {}
            
            # Extract Open Graph metadata
            for meta in soup.find_all('meta'):
                property_value = meta.get('property', '')
                if property_value.startswith('og:'):
                    metadata[property_value] = meta.get('content', '')
                    
                # Also check for description
                if meta.get('name') == 'description':
                    metadata['description'] = meta.get('content', '')
            
            # Remove common ads and navigation elements
            ad_classes = ['ad', 'ads', 'advertisement', 'banner', 'sidebar', 'social', 'share', 'comment', 'comments', 'footer']
            for class_name in ad_classes:
                for element in soup.find_all(class_=re.compile(class_name, re.IGNORECASE)):
                    element.decompose()
            
            # Try to find main content (priority to article, main, or content divs)
            main_content = None
            for tag in ['article', 'main', 'div']:
                for element in soup.find_all(tag):
                    if (tag == 'div' and any(c in element.get('class', []) for c in ['content', 'main', 'article', 'post', 'body', 'entry', 'text'])):
                        main_content = element
                        break
                    elif tag != 'div':
                        main_content = element
                        break
                if main_content:
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.body
            
            if not main_content:
                raise PluginError("No content found", plugin_name=WebScraperPlugin.__name__)
            
            # Extract text with paragraph structure
            paragraphs = []
            for p in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text(strip=True)
                if text and len(text) > 15:  # Filter out very short paragraphs
                    paragraphs.append(text)
            
            if not paragraphs:
                raise PluginError("No paragraphs found in content", plugin_name=WebScraperPlugin.__name__)
            
            # Build the result
            result = {
                "url": url,
                "title": title_text,
                "metadata": metadata,
                "content": '\n\n'.join(paragraphs),
                "content_length": len('\n\n'.join(paragraphs)),
                "paragraph_count": len(paragraphs),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Print summary
            tool_report_print(f"Extracted {len(paragraphs)} paragraphs ({result['content_length']} chars) from {url}")
            
            return result
            
        except Exception as e:
            raise PluginError(f"Error extracting smart content: {e}", plugin_name=WebScraperPlugin.__name__) from e
