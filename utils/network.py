"""
Network utility functions for the gem-assist package.
These functions are used for HTTP requests, URL operations, and web scraping.
"""

import os
import re
import json
import requests
import webbrowser
import time
from typing import Dict, Any, Optional, Union, List, Tuple
from bs4 import BeautifulSoup
from pypdl import Pypdl
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TimeRemainingColumn
from rich.text import Text
from colorama import Fore, Style
import random

from .core import tool_message_print, tool_report_print
from gem import seconds_to_hms, bytes_to_mb, format_size

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

# List of common user agents to rotate when needed
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def get_website_text_content(url: str) -> Dict[str, Any]:
    """
    Fetch and return the text content of a webpage using multiple extraction methods.
    No automatic retries as many failures are due to site restrictions rather than connectivity issues.
    
    Args:
        url: The URL of the webpage to extract content from
        
    Returns:
        Dictionary containing extracted content, extraction method used, and metadata
    """
    tool_message_print("get_website_text_content", [("url", url)])
    
    # First try the service-based method
    service_result = extract_via_service(url)
    if not service_result.get("error"):
        tool_report_print("Content extraction successful:", 
                         f"Extracted {len(service_result.get('content', ''))} characters using service method")
        return service_result
        
    # If service fails, try direct extraction
    direct_result = extract_direct(url)
    if not direct_result.get("error"):
        tool_report_print("Content extraction successful:", 
                         f"Extracted {len(direct_result.get('content', ''))} characters using direct method")
        return direct_result
    
    # Both methods failed, provide helpful recommendation
    errors = []
    if service_result.get("error"):
        errors.append(f"Service method: {service_result.get('error')}")
    if direct_result.get("error"):
        errors.append(f"Direct method: {direct_result.get('error')}")
    
    error_str = "; ".join(errors)
    
    # Check if this might be a JS-heavy site
    js_indicators = [
        "Cloudflare", "JavaScript", "ReactJS", "Vue", "Angular", 
        "dynamic content", "captcha", "authentication"
    ]
    
    recommendation = ""
    if any(indicator.lower() in error_str.lower() for indicator in js_indicators):
        recommendation = (
            " This appears to be a JavaScript-heavy site or protected by anti-scraping measures. "
            "Try using smart_content_extraction() or scrape_dynamic_content() instead."
        )
    
    final_result = {
        "error": f"Content extraction failed.{recommendation}",
        "content": "",
        "extraction_method": "failed",
        "url": url,
        "errors": errors
    }
    
    tool_report_print("Content extraction failed:", final_result["error"], is_error=True)
    return final_result

def extract_via_service(url: str) -> Dict[str, Any]:
    """Extract webpage content using the third-party service."""
    try:
        base = "https://md.dhr.wtf/?url="
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        response = requests.get(base+url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        text_content = soup.get_text(separator='\n', strip=True)
        
        # Check if content seems empty or too short
        if len(text_content) < 100:
            return {
                "error": "Content extracted is suspiciously short, possibly failed extraction",
                "content": text_content,
                "extraction_method": "service",
                "url": url
            }
            
        # Successful extraction
        return {
            "content": text_content,
            "extraction_method": "service",
            "url": url,
            "length": len(text_content)
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Service extraction failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Service extraction error: {str(e)}"}

def extract_direct(url: str) -> Dict[str, Any]:
    """Extract webpage content directly using requests and BeautifulSoup."""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Process content
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove script and style elements that we don't want to extract text from
        for element in soup(['script', 'style', 'head', 'header', 'footer', 'nav']):
            element.decompose()
        
        # Find the main content - usually in article, main, or div with content-related class/id
        main_content = None
        for selector in ['article', 'main', '.content', '#content', '.post', '.article']:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 200:
                main_content = content
                break
        
        # If no main content block found, use body
        if not main_content:
            main_content = soup.body
        
        if not main_content:
            return {"error": "Failed to locate content in the page"}
        
        # Extract text with better formatting
        paragraphs = []
        for element in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = element.get_text(strip=True)
            if text:
                if element.name.startswith('h'):
                    # Format headings with markdown-style hashes
                    level = int(element.name[1])
                    paragraphs.append(f"\n{'#' * level} {text}\n")
                else:
                    paragraphs.append(text)
        
        content = "\n\n".join(paragraphs)
        
        # Check if content seems empty or too short
        if len(content) < 100:
            return {
                "error": "Content extracted is suspiciously short, possibly failed extraction",
                "content": content,
                "extraction_method": "direct",
                "url": url
            }
            
        # Get page title
        title = soup.title.string if soup.title else "No title"
        
        # Successful extraction
        return {
            "content": content,
            "title": title,
            "extraction_method": "direct",
            "url": url,
            "length": len(content)
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Direct extraction failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Direct extraction error: {str(e)}"}

def http_get_request(url: str, headers_json: str = "") -> str:
    """
    Send an HTTP GET request to a URL and return the response as a string. Can be used for interacting with REST API's

    Args:
        url: The URL to send the request to.
        headers_json: A JSON string of headers to include in the request.

    Returns: The response from the server as a string, or an error message.
    """
    tool_message_print("http_get_request", [("url", url)])
    try:
        headers = {}
        if headers_json and isinstance(headers_json, str):
            try:
                headers = json.loads(headers_json)
            except json.JSONDecodeError as e:
                tool_report_print("Error parsing headers:", str(e), is_error=True)
                return f"Error parsing headers: {e}"

        if "User-Agent" not in headers:
            headers["User-Agent"] = DEFAULT_USER_AGENT
            
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tool_report_print("Status:", "HTTP GET request sent successfully")
        return response.text
    except requests.exceptions.RequestException as e:
        tool_report_print("Error sending HTTP GET request:", str(e), is_error=True)
        return f"Error sending HTTP GET request: {e}"
    except Exception as e:
        tool_report_print("Error processing HTTP GET request:", str(e), is_error=True)
        return f"Error processing HTTP GET request: {e}"

def http_post_request(url: str, data_json: str, headers_json: str = "") -> str:
    """
    Send an HTTP POST request to a URL with the given data and return the response as a string. Can be used for interacting with REST API's

    Args:
      url: The URL to send the request to.
      data: A dictionary containing the data to send in the request body.
      headers_json: A JSON string containing the headers to send in the request.

    Returns: The response from the server as a string, or an error message.
    """
    tool_message_print("http_post_request", [("url", url), ("data", data_json)])
    try:
        headers = {}
        if headers_json and isinstance(headers_json, str):
            try:
                headers = json.loads(headers_json)
            except json.JSONDecodeError as e:
                tool_report_print("Error parsing headers:", str(e), is_error=True)
                return f"Error parsing headers: {e}"

        if "User-Agent" not in headers:
            headers["User-Agent"] = DEFAULT_USER_AGENT

        data = json.loads(data_json)
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        tool_report_print("Status:", "HTTP POST request sent successfully")
        return response.text
    except requests.exceptions.RequestException as e:
        tool_report_print("Error sending HTTP POST request:", str(e), is_error=True)
        return f"Error sending HTTP POST request: {e}"
    except Exception as e:
        tool_report_print("Error processing HTTP POST request:", str(e), is_error=True)
        return f"Error processing HTTP POST request: {e}"

def open_url(url: str) -> bool:
    """
    Open a URL in the default web browser.

    Args:
      url: The URL to open.

    Returns: True if URL opened successfully, False otherwise.
    """
    tool_message_print("open_url", [("url", url)])
    try:
        webbrowser.open(url)
        tool_report_print("Status:", "URL opened successfully")
        return True
    except Exception as e:
        tool_report_print("Error opening URL:", str(e), is_error=True)
        return False

def progress_function(dl: Pypdl):
    """Enhanced download progress function with clearer formatting."""
    console = Console()
    progress = Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TaskProgressColumn(),
        "•",
        TimeRemainingColumn(),
    )
    
    if dl.filename:
        task_description = f"Downloading {dl.filename}"
    else:
        task_description = "Downloading file"
        
    task_id = progress.add_task(task_description, total=dl.size if dl.size else 100)
    
    def update_progress():
        if dl.size:
            progress.update(task_id, completed=dl.current_size)
            progress_bar = f"[{'█' * dl.progress}{'·' * (100 - dl.progress)}] {dl.progress}%"
            info = f"\nSize: {bytes_to_mb(dl.current_size):.2f}/{bytes_to_mb(dl.size):.2f} MB, Speed: {dl.speed:.2f} MB/s, ETA: {seconds_to_hms(dl.eta)}"
            status = progress_bar + " " + info
        else:
            progress.update(task_id, completed=dl.task_progress)
            download_stats = f"[{'█' * dl.task_progress}{'·' * (100 - dl.task_progress)}] {dl.task_progress}%" if dl.total_task > 1 else "Downloading..." if dl.task_progress else ""
            info = f"Downloaded Size: {bytes_to_mb(dl.current_size):.2f} MB, Speed: {dl.speed:.2f} MB/s"
            status = download_stats + " " + info

        return status

    with Live(Panel(Text(update_progress(), justify="left")), console=console, screen=False, redirect_stderr=False, redirect_stdout=False) as live:
        while not dl.completed:
            live.update(Panel(Text(update_progress(), justify="left")))
            time.sleep(0.1)

def resolve_filename_from_url(url: str) -> str | None:
    """
    Extract a filename from a URL either from Content-Disposition header or URL path.
    
    Args:
        url: The URL to extract filename from
        
    Returns:
        The filename if found, None otherwise
    """
    tool_message_print("resolve_filename_from_url", [("url", url)])
    
    try:
        # filename from the Content-Disposition header
        response = requests.head(url, allow_redirects=True)
        response.raise_for_status()  
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            filename_match = re.search(r"filename\*=UTF-8''([\w\-%.]+)", content_disposition) or re.search(r"filename=\"([\w\-%.]+)\"", content_disposition)
            if filename_match:
                return filename_match.group(1)

        # try to extract the filename from the URL path
        filename = url.split("/")[-1]
        if filename:
            # Further refine: remove query parameters from the filename
            filename = filename.split("?")[0]
            return filename

        return None  # Filename not found

    except requests.exceptions.RequestException as e:
        print(f"Error resolving filename from URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
def try_resolve_filename_from_url(url: str) -> tuple[str | None, str | None]:
    """
    Attempt to resolve a filename from a URL and handle errors.
    
    Args:
        url: The URL to extract filename from
        
    Returns:
        A tuple containing (filename, error_message)
        If successful, error_message will be None
        If failed, filename will be None and error_message will contain the error
    """
    try:
        filename = resolve_filename_from_url(url)
        if not filename:
            return (None, f"{Fore.RED}Error resolving filename from URL: {url}{Style.RESET_ALL}")
        return (filename, None)
    except Exception as e:
        print(f"{Fore.RED}Error resolving filename from URL: {e}{Style.RESET_ALL}")
        return (None, f"Error resolving filename from URL: {e}")

def download_file_from_url(url: str, download_path: str | None) -> str:
    """
    Downloads a file from a URL to the specified filename.
    Can download unnamed files 

    Args:
        url: The URL of the file to download.
        download_path: The path and name to save the downloaded file as. leave as None to resolve filename automatically (default None)

    Example:
        ```py
        download_file_from_url("https://example.com/file.txt", "file.txt") # with name
        download_file_from_url("https://example.com/file?id=123") # without any path cases (downloads in current directory)
        download_file_from_url("https://example.com/file.txt", "downloads/path/") # without any name (directory with slash)
        ```
    Returns:
        A string indicating the success or failure of the download.
    """
    
    try:
        # Show detailed pre-download information
        console = Console()
        console.print("[cyan]Preparing download...[/]")
        
        url_filename = None
        if download_path is None:
            console.print(f"[dim]No download path specified. Attempting to determine filename from URL...[/]")
            url_filename, error = try_resolve_filename_from_url(url)
            if error:
                return error
            final_path = url_filename  # In current directory
            console.print(f"[cyan]Detected filename: [bold]{url_filename}[/][/]")
        else:
            path_parts = os.path.split(download_path)
            final_part = path_parts[-1]
            
            is_likely_dir = (
                download_path.endswith('/') or 
                download_path.endswith('\\') or
                (os.path.isdir(download_path) if os.path.exists(download_path) else '.' not in final_part)
            )
            
            if is_likely_dir:
                console.print(f"[dim]Download path appears to be a directory. Determining filename...[/]")
                url_filename, error = try_resolve_filename_from_url(url)
                if error:
                    return error
                final_path = os.path.join(download_path, url_filename)
                console.print(f"[cyan]Will save as: [bold]{final_path}[/][/]")
            else:
                final_path = download_path
                console.print(f"[cyan]Will save as: [bold]{final_path}[/][/]")
        
        # Create directory if needed
        dir_path = os.path.dirname(os.path.abspath(final_path))
        if not os.path.exists(dir_path):
            console.print(f"[dim]Creating directory: {dir_path}[/]")
            os.makedirs(dir_path, exist_ok=True)
        
        # Start the actual download with enhanced progress tracking
        start_time = time.time()
        tool_message_print("download_file_from_url", [("url", url), ("final_path", final_path)])
        
        dl = Pypdl()
        dl.start(url, final_path, display=False, block=False)
        progress_function(dl)
        
        # Show download completion details
        download_time = time.time() - start_time
        file_size = os.path.getsize(final_path)
        tool_report_print(
            "Download complete:", 
            f"File saved to {final_path} ({format_size(file_size)})", 
            execution_time=download_time
        )
        
        return f"File downloaded successfully to {final_path} ({format_size(file_size)}) in {download_time:.2f} seconds"
    except requests.exceptions.RequestException as e:
        tool_report_print("Error downloading file:", str(e), is_error=True)
        return f"Error downloading file: {e}"
    except Exception as e:
        tool_report_print("Error downloading file:", str(e), is_error=True)
        return f"Error downloading file: {e}"

def smart_content_extraction(url: str, 
                            extract_images: bool = False, 
                            extract_links: bool = True,
                            try_dynamic: bool = True,
                            timeout: int = 20) -> Dict[str, Any]:
    """
    Intelligently extract content from a webpage, automatically choosing between static and dynamic extraction.
    Detects if a page requires JavaScript and switches to dynamic extraction if needed.
    
    Args:
        url: URL to extract content from
        extract_images: Whether to extract image information
        extract_links: Whether to extract links from the page
        try_dynamic: Whether to try dynamic extraction if static extraction appears insufficient
        timeout: Maximum time in seconds for extraction
        
    Returns:
        Dict containing extracted content and metadata
    """
    tool_message_print("smart_content_extraction", [
        ("url", url),
        ("extract_images", str(extract_images)),
        ("extract_links", str(extract_links)),
        ("try_dynamic", str(try_dynamic))
    ])
    
    # First, try regular content extraction
    try:
        regular_content = get_website_text_content(url)
        
        # If content seems empty or very short, it might need dynamic extraction
        content_text = regular_content.get('content', '')
        js_indicators = ['javascript', 'react', 'angular', 'vue', 'loading']
        
        needs_dynamic = (
            try_dynamic and (
                len(content_text) < 500 or  # Content too short
                any(f"please enable {js}" in content_text.lower() for js in js_indicators) or
                "loading" in content_text.lower() or
                regular_content.get('error')  # Error in static extraction
            )
        )
        
        if needs_dynamic:
            try:
                # Import at the point of use to avoid dependency issues
                from utils.web_scraper import scrape_dynamic_content
                
                tool_report_print("Static extraction insufficient:", 
                                 "Switching to dynamic content extraction")
                
                dynamic_result = scrape_dynamic_content(
                    url=url,
                    wait_time=10,
                    selector_to_wait_for="body"
                )
                
                # If dynamic extraction worked, use that instead
                if dynamic_result and not dynamic_result.get('error'):
                    dynamic_result['extraction_method'] = 'dynamic'
                    return dynamic_result
            except ImportError:
                tool_report_print("Dynamic extraction unavailable:", 
                                 "Selenium not installed, continuing with static content")
            except Exception as e:
                tool_report_print("Dynamic extraction failed:", str(e), is_error=True)
        
        # Add additional extraction if requested
        if extract_links or extract_images:
            from utils.web_scraper import extract_structured_data
            
            try:
                data_types = []
                if extract_links:
                    data_types.append('links')
                if extract_images:
                    data_types.append('images')
                
                structured_data = extract_structured_data(
                    url=url,
                    data_type=','.join(data_types)
                )
                
                if extract_links and 'links' in structured_data:
                    regular_content['links'] = structured_data.get('links', [])
                    
                if extract_images and 'images' in structured_data:
                    regular_content['images'] = structured_data.get('images', [])
                    
            except Exception as e:
                tool_report_print("Enhanced extraction failed:", str(e), is_error=True)
        
        regular_content['extraction_method'] = 'static'
        return regular_content
        
    except Exception as e:
        tool_report_print("Smart content extraction failed:", str(e), is_error=True)
        return {"error": f"Content extraction failed: {str(e)}"}
