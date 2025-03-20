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
from bs4 import BeautifulSoup
from pypdl import Pypdl
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TimeRemainingColumn
from rich.text import Text
from colorama import Fore, Style

from .core import tool_message_print, tool_report_print
from gem import seconds_to_hms, bytes_to_mb, format_size

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

def get_website_text_content(url: str) -> str:
    """
    Fetch and return the text content of a webpage/article in nicely formatted markdown for easy readability.
    It doesn't contain everything, just links and text contents
    DONT USE THIS FOR REDDIT POST, use `get_reddit_post` for that

    Args:
      url: The URL of the webpage.

    Returns: The text content of the website in markdown format, or an error message.
    """
    tool_message_print("get_website_text_content", [("url", url)])
    try:
        base = "https://md.dhr.wtf/?url="
        response = requests.get(base+url, headers={'User-Agent': DEFAULT_USER_AGENT})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'lxml')
        text_content = soup.get_text(separator='\n', strip=True) 
        tool_report_print("Status:", "Webpage content fetched successfully")
        return text_content
    except requests.exceptions.RequestException as e:
        tool_report_print("Error fetching webpage content:", str(e), is_error=True)
        return f"Error fetching webpage content: {e}"
    except Exception as e:
        tool_report_print("Error processing webpage content:", str(e), is_error=True)
        return f"Error processing webpage content: {e}"
    
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
