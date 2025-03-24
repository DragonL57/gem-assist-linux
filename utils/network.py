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
from urllib.parse import urljoin
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

# Constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
DEFAULT_TIMEOUT = 15
MAX_LINKS_EXTRACT = 50
MAX_IMAGES_EXTRACT = 20

# Common user agents to rotate for avoiding bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

# Check for optional dependencies
YOUTUBE_TRANSCRIPT_API_AVAILABLE = False
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    YOUTUBE_TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    pass

class WebContentExtractor:
    """Handles extraction of web content with various strategies."""
    
    @staticmethod
    def get_website_text_content(
        url: str, 
        extract_mode: str = "auto",
        extract_links: bool = False,
        extract_images: bool = False,
        extract_metadata: bool = True,
        focus_element: str = None,
        fallback_to_dynamic: bool = False,
        timeout: int = DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Enhanced webpage content extraction with multiple options for controlling output.
        
        Args:
            url: The URL of the webpage to extract content from
            extract_mode: Extraction method to use ("auto", "service", "direct")
            extract_links: Whether to extract links from the page
            extract_images: Whether to extract images from the page
            extract_metadata: Whether to include metadata like title, description
            focus_element: CSS selector to focus extraction on (e.g., "article", ".content")
            fallback_to_dynamic: Whether to try dynamic extraction if initial methods fail
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing extracted content, metadata, and additional elements if requested
        """
        tool_message_print("get_website_text_content", [
            ("url", url),
            ("extract_mode", extract_mode),
            ("extract_links", str(extract_links)),
            ("extract_images", str(extract_images)),
            ("extract_metadata", str(extract_metadata)),
            ("focus_element", focus_element or "None"),
            ("fallback_to_dynamic", str(fallback_to_dynamic))
        ])
        
        result = None
        errors = []
        
        # Step 1: Try the requested extraction method(s)
        if extract_mode in ("auto", "service"):
            service_result = WebContentExtractor._extract_via_service(url)
            if not service_result.get("error"):
                result = service_result
            else:
                errors.append(f"Service method: {service_result.get('error')}")
        
        if extract_mode in ("auto", "direct") and (result is None or result.get("error")):
            direct_result = WebContentExtractor._extract_direct(url, focus_element, timeout)
            if not direct_result.get("error"):
                result = direct_result
            else:
                errors.append(f"Direct method: {direct_result.get('error')}")
        
        # Step 2: Try dynamic extraction if needed and enabled
        if (result is None or result.get("error")) and fallback_to_dynamic:
            dynamic_result = WebContentExtractor._try_dynamic_extraction(url, focus_element, timeout)
            if dynamic_result and not dynamic_result.get("error"):
                result = dynamic_result
            else:
                errors.append(dynamic_result.get("error", "Dynamic extraction failed"))
        
        # Step 3: Enhance successful result with requested data
        if result and not result.get("error"):
            WebContentExtractor._enhance_extraction_result(
                result, url, extract_metadata, extract_links, extract_images, timeout
            )
            
            content_length = len(result.get("content", ""))
            tool_report_print("Content extraction successful:", 
                            f"Extracted {content_length} characters using {result.get('extraction_method', 'unknown')} method")
            return result
        
        # Step 4: Handle failure
        return WebContentExtractor._build_error_response(url, errors, fallback_to_dynamic)
    
    @staticmethod
    def _extract_via_service(url: str) -> Dict[str, Any]:
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
    
    @staticmethod
    def _extract_direct(url: str, focus_element: str = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
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
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Process content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove script and style elements that we don't want to extract text from
            for element in soup(['script', 'style', 'head', 'header', 'footer', 'nav']):
                element.decompose()
            
            # Find main content area
            main_content = WebContentExtractor._locate_main_content(soup, focus_element)
            if not main_content:
                return {"error": "Failed to locate content in the page"}
            
            # Extract formatted content
            content = WebContentExtractor._extract_formatted_content(main_content)
            
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
    
    @staticmethod
    def _locate_main_content(soup: BeautifulSoup, focus_element: str = None) -> Optional[Any]:
        """Find the main content area of a webpage."""
        # Use focus element if provided
        if focus_element:
            content = soup.select_one(focus_element)
            if content and len(content.get_text(strip=True)) > 50:
                return content
        
        # Try common content selectors
        selectors = [
            'article', 'main', '.content', '#content', '.post', 
            '.article', '.entry-content', '#main', '.blog-content',
            '.page-content', '[role="main"]'
        ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 200:
                return content
        
        # If no main content block found, use body
        return soup.body
    
    @staticmethod
    def _extract_formatted_content(element: Any) -> str:
        """Extract formatted content from HTML elements."""
        paragraphs = []
        for elem in element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'pre', 'blockquote']):
            text = elem.get_text(strip=True)
            if not text:
                continue
                
            if elem.name.startswith('h'):
                # Format headings with markdown-style hashes
                level = int(elem.name[1])
                paragraphs.append(f"\n{'#' * level} {text}\n")
            elif elem.name == 'li':
                # Format list items
                paragraphs.append(f"* {text}")
            elif elem.name == 'pre':
                # Format code blocks
                paragraphs.append(f"```\n{text}\n```")
            else:
                paragraphs.append(text)
        
        return "\n\n".join(paragraphs)
    
    @staticmethod
    def _try_dynamic_extraction(url: str, focus_element: str = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Attempt dynamic content extraction using Selenium."""
        try:
            from utils.web_scraper import scrape_dynamic_content
            tool_report_print("Static extraction failed:", "Trying dynamic content extraction")
            
            dynamic_result = scrape_dynamic_content(url=url, wait_time=timeout, 
                                                  selector_to_wait_for=focus_element or "body")
            
            if not dynamic_result.get("error"):
                dynamic_result["extraction_method"] = "dynamic"
                return dynamic_result
            else:
                return {"error": dynamic_result.get("error", "Dynamic extraction failed")}
        except ImportError:
            return {"error": "Dynamic extraction unavailable: selenium not installed"}
        except Exception as e:
            return {"error": f"Dynamic extraction failed: {str(e)}"}
    
    @staticmethod
    def _enhance_extraction_result(
        result: Dict[str, Any], url: str, extract_metadata: bool, 
        extract_links: bool, extract_images: bool, timeout: int
    ) -> None:
        """Enhance extraction result with metadata, links, and images if requested."""
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        # Add metadata if requested and not already present
        if extract_metadata and "title" not in result:
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract basic metadata
                result["title"] = soup.title.string if soup.title else "No title"
                
                # Extract meta description
                desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                if desc_tag and desc_tag.get("content"):
                    result["description"] = desc_tag.get("content")
                
                # Extract author if available
                author_tag = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", attrs={"property": "og:author"})
                if author_tag and author_tag.get("content"):
                    result["author"] = author_tag.get("content")
                
                # Extract publication date if available
                date_tag = soup.find("meta", attrs={"name": "date"}) or soup.find("meta", attrs={"property": "article:published_time"})
                if date_tag and date_tag.get("content"):
                    result["published_date"] = date_tag.get("content")
            except Exception as e:
                result["metadata_error"] = str(e)
        
        # Extract links if requested
        if extract_links and "links" not in result:
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href and href != "#":
                        # Handle relative URLs
                        if href.startswith('/'):
                            href = urljoin(url, href)
                        links.append({"url": href, "text": text or "[No text]"})
                
                result["links"] = links[:MAX_LINKS_EXTRACT]  # Limit to first 50 links to avoid excessive output
                result["total_links"] = len(links)
            except Exception as e:
                result["links_error"] = str(e)
        
        # Extract images if requested
        if extract_images and "images" not in result:
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                images = []
                for img in soup.find_all('img', src=True):
                    src = img.get('src')
                    alt = img.get('alt', '')
                    if src:
                        # Handle relative URLs
                        if src.startswith('/'):
                            src = urljoin(url, src)
                        images.append({"url": src, "alt": alt or "[No alt text]"})
                
                result["images"] = images[:MAX_IMAGES_EXTRACT]  # Limit to first 20 images
                result["total_images"] = len(images)
            except Exception as e:
                result["images_error"] = str(e)
    
    @staticmethod
    def _build_error_response(url: str, errors: List[str], fallback_to_dynamic: bool) -> Dict[str, Any]:
        """Build error response for failed content extraction."""
        error_str = "; ".join(errors)
        
        # Check if this might be a JS-heavy site
        js_indicators = [
            "Cloudflare", "JavaScript", "ReactJS", "Vue", "Angular", 
            "dynamic content", "captcha", "authentication"
        ]
        
        recommendation = ""
        if any(indicator.lower() in error_str.lower() for indicator in js_indicators):
            if not fallback_to_dynamic:
                recommendation = (
                    " This appears to be a JavaScript-heavy site. "
                    "Try using this function with fallback_to_dynamic=True or use scrape_dynamic_content() directly."
                )
            else:
                recommendation = " This site may be protected against scraping."
        
        final_result = {
            "error": f"Content extraction failed.{recommendation}",
            "content": "",
            "extraction_method": "failed",
            "url": url,
            "errors": errors
        }
        
        tool_report_print("Content extraction failed:", final_result["error"], is_error=True)
        return final_result

# Update the existing content extraction function to use the new WebContentExtractor class
def get_website_text_content(
    url: str, 
    extract_mode: str = "auto",
    extract_links: bool = False,
    extract_images: bool = False,
    extract_metadata: bool = True,
    focus_element: str = None,
    fallback_to_dynamic: bool = False,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    Enhanced webpage content extraction with multiple options for controlling output.
    
    Args:
        url: The URL of the webpage to extract content from
        extract_mode: Extraction method to use ("auto", "service", "direct")
        extract_links: Whether to extract links from the page
        extract_images: Whether to extract images from the page
        extract_metadata: Whether to include metadata like title, description
        focus_element: CSS selector to focus extraction on (e.g., "article", ".content")
        fallback_to_dynamic: Whether to try dynamic extraction if initial methods fail
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary containing extracted content, metadata, and additional elements if requested
    """
    return WebContentExtractor.get_website_text_content(
        url=url,
        extract_mode=extract_mode,
        extract_links=extract_links,
        extract_images=extract_images,
        extract_metadata=extract_metadata,
        focus_element=focus_element,
        fallback_to_dynamic=fallback_to_dynamic,
        timeout=timeout
    )

# Existing extract_via_service and extract_direct functions are maintained for backward compatibility
# but now they delegate to the WebContentExtractor class

def extract_via_service(url: str) -> Dict[str, Any]:
    """Extract webpage content using the third-party service."""
    return WebContentExtractor._extract_via_service(url)

def extract_direct(url: str, focus_element: str = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Extract webpage content directly using requests and BeautifulSoup."""
    return WebContentExtractor._extract_direct(url, focus_element, timeout)

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
        regular_content = WebContentExtractor.get_website_text_content(url)
        
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

def get_youtube_transcript(video_url_or_id: str, 
                          languages: str = "en", 
                          format_timestamps: bool = True,
                          combine_segments: bool = False) -> Dict[str, Any]:
    """
    Extract transcript (captions/subtitles) from a YouTube video.
    
    This tool allows you to get the full transcript text from any YouTube video by providing
    either the complete YouTube URL or just the video ID. Supports multiple languages and
    various formatting options.
    
    Args:
        video_url_or_id: YouTube video URL (e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ) 
                         or just the video ID (e.g., dQw4w9WgXcQ)
        languages: Comma-separated language codes in order of preference (e.g., "en,fr,es")
        format_timestamps: Whether to format timestamps as HH:MM:SS
        combine_segments: Whether to combine all segments into a single text
        
    Returns:
        Dictionary containing video info and transcript with timestamps
    """
    tool_message_print("get_youtube_transcript", [
        ("video_url_or_id", video_url_or_id),
        ("languages", languages),
        ("format_timestamps", str(format_timestamps)),
        ("combine_segments", str(combine_segments))
    ])
    
    if not YOUTUBE_TRANSCRIPT_API_AVAILABLE:
        error_message = "youtube_transcript_api is not installed. Install with: uv pip install youtube-transcript-api"
        tool_report_print("Error:", error_message, is_error=True)
        return {"error": error_message}
    
    try:
        # Extract video ID from URL if needed
        video_id = extract_youtube_video_id(video_url_or_id)
        if not video_id:
            tool_report_print("Error:", "Invalid YouTube URL or video ID", is_error=True)
            return {"error": "Invalid YouTube URL or video ID"}
        
        # Parse language preferences
        language_list = [lang.strip() for lang in languages.split(",")]
        
        # Get transcript directly - simpler approach
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=language_list)
            used_language = language_list[0] if language_list else "en"  # Default to first requested language
        except NoTranscriptFound:
            # Try getting available transcripts and translating
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Get any transcript and translate to first preferred language
                transcript = next(transcript_list)
                if language_list:
                    transcript = transcript.translate(language_list[0])
                    used_language = f"{transcript.language_code} (translated to {language_list[0]})"
                else:
                    used_language = transcript.language_code
                transcript_data = transcript.fetch()
            except Exception as e:
                tool_report_print("Error:", f"No transcript found: {str(e)}", is_error=True)
                return {"error": f"No transcript found: {str(e)}"}
        
        # Format timestamps if requested
        if format_timestamps:
            for entry in transcript_data:
                seconds = int(entry['start'])
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)
                entry['formatted_timestamp'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Combine segments if requested
        combined_text = None
        if combine_segments:
            combined_text = " ".join(entry['text'] for entry in transcript_data)
        
        # Get video title and other metadata
        video_title = "YouTube Video"
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Try to get video title from page
            headers = {'User-Agent': DEFAULT_USER_AGENT}
            response = requests.get(video_url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    video_title = title_tag.text.replace(' - YouTube', '')
        except Exception as e:
            # If we can't get the title, just continue with default
            pass
        
        result = {
            "video_id": video_id,
            "video_url": video_url,
            "video_title": video_title,
            "language": used_language,
            "transcript_segments": transcript_data,
            "segment_count": len(transcript_data)
        }
        
        if combined_text:
            result["combined_text"] = combined_text
        
        tool_report_print("Transcript retrieved:", 
                         f"Found {len(transcript_data)} segments in language: {used_language}")
        return result
        
    except VideoUnavailable:
        tool_report_print("Error:", "The video is unavailable (possibly private or deleted)", is_error=True)
        return {"error": "The video is unavailable (possibly private or deleted)"}
    except TranscriptsDisabled:
        tool_report_print("Error:", "Transcripts are disabled for this video", is_error=True)
        return {"error": "Transcripts are disabled for this video"}
    except Exception as e:
        tool_report_print("Error retrieving transcript:", str(e), is_error=True)
        return {"error": f"Failed to retrieve transcript: {str(e)}"}

def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube video ID from a URL or return the ID if already in correct format."""
    if not url_or_id:
        return None
    
    # Check if it's already an ID (simple 11 character string)
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Try to extract ID from various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/\?v=)([A-Za-z0-9_-]{11})',
        r'(?:youtube\.com\/watch\?.*v=)([A-Za-z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None
