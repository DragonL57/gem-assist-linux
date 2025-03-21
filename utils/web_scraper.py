"""
Enhanced web scraping utilities for the gem-assist package.
Provides tools for extracting structured data from web pages.
"""

import re
import time
from typing import Dict, List, Union, Optional

# Handle optional dependencies
REQUESTS_AVAILABLE = False
BEAUTIFULSOUP_AVAILABLE = False
PANDAS_AVAILABLE = False
SELENIUM_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    pass

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    pass

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

# Try importing Selenium for dynamic content
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

from .core import tool_message_print, tool_report_print

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

def extract_structured_data(url: str, data_type: str = "all") -> Dict:
    """
    Extract structured data (tables, lists, headings) from a webpage.
    
    Args:
        url: The URL of the webpage to scrape
        data_type: Type of data to extract ('tables', 'lists', 'headings', 'links', or 'all')
        
    Returns:
        Dictionary containing the extracted structured data
    """
    tool_message_print("extract_structured_data", [("url", url), ("data_type", data_type)])
    
    if not REQUESTS_AVAILABLE or not BEAUTIFULSOUP_AVAILABLE:
        missing = []
        if not REQUESTS_AVAILABLE:
            missing.append("requests")
        if not BEAUTIFULSOUP_AVAILABLE:
            missing.append("beautifulsoup4")
        
        error_message = f"Missing required packages: {', '.join(missing)}. Please install them with: uv pip install {' '.join(missing)}"
        tool_report_print("Error extracting structured data:", error_message, is_error=True)
        return {"error": error_message}
    
    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        result = {"url": url, "title": soup.title.string if soup.title else "No title"}
        
        # Extract tables
        if data_type in ["all", "tables"]:
            tables = []
            for i, table in enumerate(soup.find_all('table')):
                table_data = []
                
                # Get table headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
                
                # Get table rows
                rows = []
                for tr in table.find_all('tr')[1:] if headers else table.find_all('tr'):
                    row = [td.text.strip() for td in tr.find_all(['td', 'th'])]
                    if row and any(cell for cell in row):  # Skip empty rows
                        rows.append(row)
                
                table_data = {
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows)
                }
                tables.append(table_data)
            
            result["tables"] = tables
            
        # Extract lists
        if data_type in ["all", "lists"]:
            lists = []
            for i, list_elem in enumerate(soup.find_all(['ul', 'ol'])):
                list_type = list_elem.name
                items = [li.text.strip() for li in list_elem.find_all('li')]
                if items:  # Skip empty lists
                    lists.append({
                        "type": list_type,
                        "items": items
                    })
            result["lists"] = lists
        
        # Extract headings
        if data_type in ["all", "headings"]:
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for heading in soup.find_all(tag):
                    text = heading.text.strip()
                    if text:  # Skip empty headings
                        headings.append({
                            "level": int(tag[1]),
                            "text": text
                        })
            result["headings"] = headings
        
        # Extract links
        if data_type in ["all", "links"]:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.text.strip()
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    # Make relative URLs absolute
                    if href.startswith('/'):
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        href = base_url + href
                    
                    links.append({
                        "text": text if text else "No text",
                        "href": href
                    })
            result["links"] = links
        
        tool_report_print("Structured data extracted:", f"Successfully extracted {data_type} data from {url}")
        return result
        
    except Exception as e:
        tool_report_print("Error extracting structured data:", str(e), is_error=True)
        return {"error": f"Failed to extract data: {str(e)}"}

def extract_tables_to_dataframes(url: str) -> Dict[str, pd.DataFrame]:
    """
    Extract tables from a webpage and convert them to pandas DataFrames.
    
    Args:
        url: The URL of the webpage containing tables
        
    Returns:
        Dictionary of table names to pandas DataFrames
    """
    tool_message_print("extract_tables_to_dataframes", [("url", url)])
    
    if not PANDAS_AVAILABLE:
        error_message = "pandas library is not installed. Please install it with: uv pip install pandas"
        tool_report_print("Error extracting tables:", error_message, is_error=True)
        return {"error": error_message}
    
    try:
        # Use pandas' built-in table extraction
        tables = pd.read_html(url)
        
        result = {}
        for i, df in enumerate(tables):
            result[f"table_{i+1}"] = df
        
        tool_report_print("Tables extracted:", f"Successfully extracted {len(tables)} tables as DataFrames")
        return result
    
    except Exception as e:
        tool_report_print("Error extracting tables:", str(e), is_error=True)
        return {"error": f"Failed to extract tables: {str(e)}"}

def scrape_with_pagination(base_url: str, max_pages: int = 3, page_param: str = "page", 
                          start_page: int = 1, content_selector: str = "body") -> Dict:
    """
    Scrape content from multiple pages with pagination.
    
    Args:
        base_url: The base URL to scrape (should contain {page} if not using page_param)
        max_pages: Maximum number of pages to scrape
        page_param: URL parameter used for pagination
        start_page: Page number to start from
        content_selector: CSS selector for the content to extract
        
    Returns:
        Dictionary with extracted content from all pages
    """
    tool_message_print("scrape_with_pagination", [
        ("base_url", base_url),
        ("max_pages", str(max_pages)),
        ("page_param", page_param),
        ("start_page", str(start_page))
    ])
    
    if not REQUESTS_AVAILABLE or not BEAUTIFULSOUP_AVAILABLE:
        missing = []
        if not REQUESTS_AVAILABLE:
            missing.append("requests")
        if not BEAUTIFULSOUP_AVAILABLE:
            missing.append("beautifulsoup4")
        
        error_message = f"Missing required packages: {', '.join(missing)}. Please install them with: uv pip install {' '.join(missing)}"
        tool_report_print("Error during multi-page scraping:", error_message, is_error=True)
        return {"error": error_message}
    
    results = {"pages": []}
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    
    try:
        for page_num in range(start_page, start_page + max_pages):
            # Construct the page URL
            if "{page}" in base_url:
                page_url = base_url.format(page=page_num)
            else:
                separator = "&" if "?" in base_url else "?"
                page_url = f"{base_url}{separator}{page_param}={page_num}"
            
            # Request the page
            response = requests.get(page_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the content
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.select(content_selector)
            
            page_content = "".join(str(element) for element in content)
            
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
        
        tool_report_print("Multi-page scraping complete:", f"Scraped {len(results['pages'])} pages")
        return results
        
    except Exception as e:
        tool_report_print("Error during multi-page scraping:", str(e), is_error=True)
        return {"error": f"Failed to scrape pages: {str(e)}", "pages_completed": len(results["pages"])}

def scrape_dynamic_content(url: str, wait_time: int = 5, 
                          selector_to_wait_for: str = None) -> Dict:
    """
    Scrape content from a dynamic webpage that requires JavaScript using Selenium.
    
    Args:
        url: The URL to scrape
        wait_time: Time to wait for the page to load (in seconds)
        selector_to_wait_for: CSS selector to wait for before extracting content
        
    Returns:
        Dictionary with the extracted content
    """
    tool_message_print("scrape_dynamic_content", [
        ("url", url),
        ("wait_time", str(wait_time)),
        ("selector_to_wait_for", selector_to_wait_for or "None")
    ])
    
    if not SELENIUM_AVAILABLE:
        error_message = "Selenium is not installed. Please install it with: uv pip install selenium"
        tool_report_print("Error scraping dynamic content:", error_message, is_error=True)
        return {"error": error_message}
    
    if not BEAUTIFULSOUP_AVAILABLE:
        error_message = "BeautifulSoup4 is not installed. Please install it with: uv pip install beautifulsoup4"
        tool_report_print("Error scraping dynamic content:", error_message, is_error=True)
        return {"error": error_message}
    
    driver = None
    try:
        # Set up Chrome options for headless operation
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")
        
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Wait for specific element or general page load
        if selector_to_wait_for:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector_to_wait_for))
            )
        else:
            time.sleep(wait_time)
        
        # Get the page source after JavaScript has been executed
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        result = {
            "url": url,
            "title": driver.title,
            "content": soup.get_text(separator='\n', strip=True)
        }
        
        # Extract structured data after JavaScript execution
        result.update(extract_structured_data_from_soup(soup))
        
        tool_report_print("Dynamic content scraped:", f"Successfully scraped dynamic content from {url}")
        return result
        
    except TimeoutException:
        tool_report_print("Error scraping dynamic content:", 
                         f"Timed out waiting for element: {selector_to_wait_for}", is_error=True)
        return {"error": f"Timed out waiting for element: {selector_to_wait_for}"}
        
    except Exception as e:
        tool_report_print("Error scraping dynamic content:", str(e), is_error=True)
        return {"error": f"Failed to scrape dynamic content: {str(e)}"}
        
    finally:
        # Always close the driver to avoid resource leaks
        if driver:
            driver.quit()

def extract_structured_data_from_soup(soup: BeautifulSoup) -> Dict:
    """Helper method to extract structured data from a BeautifulSoup object"""
    if not BEAUTIFULSOUP_AVAILABLE:
        return {}
    
    result = {}
    
    # Extract tables
    tables = []
    for table in soup.find_all('table'):
        headers = [th.text.strip() for th in table.find_all('th')]
        rows = []
        for tr in table.find_all('tr'):
            row = [td.text.strip() for td in tr.find_all('td')]
            if row:  # Skip header rows without data
                rows.append(row)
        
        if headers or rows:
            tables.append({"headers": headers, "rows": rows})
    
    result["tables"] = tables
    
    # Extract other structures as needed
    # (similar to the extract_structured_data function)
    
    return result
