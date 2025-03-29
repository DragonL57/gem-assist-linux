# Previous content remains the same up until get_youtube_transcript method
"""
Network plugin providing web and internet operations.
"""
import os
import requests
import random
import urllib.parse
import time
import re
from typing import Dict, Any, List, Optional

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print

class NetworkPlugin(Plugin):
    """Plugin providing network operations."""
    
    # Common user agents to rotate for avoiding bot detection
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    ]
    
    @staticmethod
    @tool(
        categories=["web", "content"],
        requires_network=True,
        rate_limited=True,
        example_usage="get_website_text_content('https://example.com')"
    )
    def get_website_text_content(url: str) -> str:
        """
        Extract text content from a webpage.
        
        Args:
            url: The URL of the website to extract text from
            
        Returns:
            Extracted text content
        """
        tool_message_print(f"Fetching content from: {url}")
        
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Use a random user agent
            headers = {'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Use BeautifulSoup for parsing
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script_or_style in soup(['script', 'style', 'header', 'footer', 'nav']):
                script_or_style.decompose()
                
            # Extract text
            text = soup.get_text(separator='\n')
            
            # Clean up text: remove excessive newlines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            return text
            
        except Exception as e:
            raise PluginError(f"Error fetching website content: {e}", plugin_name=NetworkPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "api"],
        requires_network=True,
        rate_limited=True
    )
    def http_get_request(
        url: str, 
        params: Dict[str, str] = None, 
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP GET request to a URL.
        
        Args:
            url: The URL to request
            params: Optional query parameters as key-value pairs (e.g. {"q": "search term", "page": "1"})
            headers: Optional HTTP headers as key-value pairs (e.g. {"User-Agent": "Custom Agent", "Accept": "application/json"})
            
        Returns:
            Dictionary containing response information
        """
        tool_message_print(f"Making GET request to: {url}")
        
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Use default headers if none provided
            if not headers:
                headers = {'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
                
            # Make the request
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            # Build the result
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get('Content-Type', 'unknown'),
                "url": response.url,
            }
            
            # Add text content if it's text
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text' in content_type or 'json' in content_type or 'xml' in content_type:
                result["text"] = response.text
                
                # Parse JSON if applicable
                if 'json' in content_type:
                    try:
                        result["json"] = response.json()
                    except:
                        pass
            else:
                result["content_length"] = len(response.content)
                
            return result
            
        except Exception as e:
            raise PluginError(f"Error making http GET request: {e}", plugin_name=NetworkPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "multimedia"],
        requires_network=True,
        rate_limited=True
    )
    def get_youtube_transcript(video_url: str, languages: List[str] = None) -> str:
        """
        Get the transcript of a YouTube video. 
        
        Args:
            video_url: YouTube video URL or ID
            languages: Preferred languages for transcript (default: ['en'])
            
        Returns:
            Video transcript text
        """
        tool_message_print(f"Getting transcript for: {video_url}")
        
        try:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
            except ImportError:
                raise PluginError(
                    "youtube_transcript_api package is required for this tool",
                    plugin_name=NetworkPlugin.__name__
                )
            
            if languages is None:
                languages = ['en']
            
            # Extract video ID from URL if needed
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                if 'youtube.com/watch' in video_url:
                    query = urllib.parse.urlparse(video_url).query
                    params = urllib.parse.parse_qs(query)
                    video_id = params.get('v', [''])[0]
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                else:
                    raise PluginError(
                        "Could not extract video ID from URL",
                        plugin_name=NetworkPlugin.__name__
                    )
            else:
                # Assume the input is already a video ID
                video_id = video_url
                
            if not video_id:
                raise PluginError("No video ID found", plugin_name=NetworkPlugin.__name__)
                
            # Try to get transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # First try: Get transcript in one of the specified languages
            try:
                transcript = transcript_list.find_transcript(languages)
            except Exception:
                # Second try: Get English transcript if available
                try:
                    transcript = transcript_list.find_transcript(['en'])
                except Exception:
                    # If all fails, try to get any available transcript
                    try:
                        transcript = next(iter(transcript_list._manually_created_transcripts.values()), 
                                       next(iter(transcript_list._generated_transcripts.values()), None))
                    except Exception:
                        raise PluginError(
                            "No transcript available for this video",
                            plugin_name=NetworkPlugin.__name__
                        )
            
            if not transcript:
                raise PluginError(
                    "No transcript available for this video",
                    plugin_name=NetworkPlugin.__name__
                )
                
            # Fetch the transcript data
            transcript_data = transcript.fetch()
            
            # Format the transcript with timestamps
            formatted_transcript = []
            for entry in transcript_data:
                try:
                    # Handle both dictionary entries and object entries
                    if hasattr(entry, 'start') and hasattr(entry, 'text'):
                        # It's an object with attributes
                        start_time = int(entry.start)
                        text = entry.text.strip()
                    elif isinstance(entry, dict):
                        # It's a dictionary
                        start_time = int(entry.get('start', 0))
                        text = entry.get('text', '').strip()
                    else:
                        # Unknown format, try direct access
                        start_time = int(entry['start']) if 'start' in entry else 0
                        text = str(entry['text']).strip() if 'text' in entry else ''
                    
                    minutes = start_time // 60
                    seconds = start_time % 60
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"
                    formatted_transcript.append(f"{timestamp} {text}")
                except (KeyError, TypeError, ValueError, AttributeError):
                    # Skip problematic entries
                    continue
            
            # Add video title if we can get it
            try:
                response = requests.get(
                    f"https://www.youtube.com/watch?v={video_id}",
                    headers={'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
                )
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title').text.replace(' - YouTube', '')
                header = f"Video: {title}\n\n"
            except Exception:
                header = ""
            
            # Join transcript parts
            result = header + "\n".join(formatted_transcript)
            
            tool_report_print(f"Successfully retrieved transcript with {len(formatted_transcript)} segments")
            return result
            
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Error getting youtube transcript: {e}", plugin_name=NetworkPlugin.__name__) from e

    # Rest of the file remains the same
    @staticmethod
    @tool(
        categories=["web", "api"],
        requires_network=True,
        rate_limited=True
    )
    def http_post_request(
        url: str, 
        data: Dict[str, Any] = None, 
        json_data: Dict[str, Any] = None, 
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP POST request to a URL.
        
        Args:
            url: The URL to request
            data: Optional form data as key-value pairs (e.g. {"name": "value", "other": "data"})
            json_data: Optional JSON data as key-value pairs (e.g. {"key": "value", "nested": {"data": 123}})
            headers: Optional HTTP headers as key-value pairs (e.g. {"Content-Type": "application/json"})
            
        Returns:
            Dictionary containing response information
        """
        tool_message_print(f"Making POST request to: {url}")
        
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Use default headers if none provided
            if not headers:
                headers = {'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
                
            # Make the request
            response = requests.post(url, data=data, json=json_data, headers=headers, timeout=15)
            
            # Build the result
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get('Content-Type', 'unknown'),
                "url": response.url,
            }
            
            # Add text content if it's text
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text' in content_type or 'json' in content_type or 'xml' in content_type:
                result["text"] = response.text
                
                # Parse JSON if applicable
                if 'json' in content_type:
                    try:
                        result["json"] = response.json()
                    except:
                        pass
            else:
                result["content_length"] = len(response.content)
                
            return result
            
        except Exception as e:
            raise PluginError(f"Error making http POST request: {e}", plugin_name=NetworkPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "browser"],
        requires_network=True
    )
    def open_url(url: str) -> Dict[str, Any]:
        """
        Open a URL in the default web browser. 
        
        Args:
            url: The URL to open
            
        Returns:
            Dictionary with status information
        """
        tool_message_print(f"Opening URL in browser: {url}")
        
        try:
            import webbrowser
            
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Open the URL in the default browser
            success = webbrowser.open(url)
            
            if success:
                return {
                    "success": True,
                    "url": url,
                    "message": f"URL opened in default browser: {url}"
                }
            else:
                raise PluginError(
                    "Failed to open URL in browser",
                    plugin_name=NetworkPlugin.__name__
                )
                
        except Exception as e:
            raise PluginError(f"Error opening URL in browser: {e}", plugin_name=NetworkPlugin.__name__) from e
    
    @staticmethod
    @tool(
        categories=["web", "download"],
        requires_network=True,
        requires_filesystem=True
    )
    def download_file_from_url(url: str, output_path: str = None, chunk_size: int = 8192) -> Dict[str, Any]:
        """
        Download a file from a URL. 
        
        Args:
            url: URL of the file to download
            output_path: Path where the file should be saved (default: auto-generated from URL)
            chunk_size: Size of download chunks in bytes
            
        Returns:
            Dictionary with download information
        """
        tool_message_print(f"Downloading file from: {url}")
        
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Make a HEAD request to get headers
            headers = {'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
            head_response = requests.head(url, headers=headers, allow_redirects=True)
            
            # If output_path is not specified, generate one from URL or Content-Disposition
            if output_path is None:
                filename = NetworkPlugin.resolve_filename_from_url(url, head_response.headers)
                output_path = os.path.join(os.getcwd(), filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Start the download
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get content length if available
            content_length = int(response.headers.get('Content-Length', 0))
            
            # Download the file in chunks
            downloaded = 0
            start_time = time.time()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            # Calculate download time and speed
            download_time = time.time() - start_time
            speed_kbps = (downloaded / 1024) / download_time if download_time > 0 else 0
            
            # Get file info
            file_size = os.path.getsize(output_path)
            
            return {
                "success": True,
                "url": url,
                "file_path": output_path,
                "file_size": file_size,
                "download_time_seconds": round(download_time, 2),
                "speed_kbps": round(speed_kbps, 2),
                "content_type": response.headers.get('Content-Type', 'unknown')
            }
            
        except Exception as e:
            raise PluginError(f"Error downloading file from url: {e}", plugin_name=NetworkPlugin.__name__) from e
    
    @staticmethod
    def resolve_filename_from_url(url: str, headers: Dict[str, str] = None) -> str:
        """
        Resolve a filename from URL and response headers. 
        
        Args:
            url: The URL of the file
            headers: Response headers from a HEAD request
            
        Returns:
            Resolved filename
        """
        try:
            # Try to get filename from Content-Disposition header
            if headers and 'Content-Disposition' in headers:
                content_disposition = headers['Content-Disposition']
                filename_match = re.search(r'filename=[\'"]?([^\'"\s]+)[\'"]?', content_disposition)
                if filename_match:
                    return filename_match.group(1)
            
            # Try to get filename from URL path
            parsed_url = urllib.parse.urlparse(url)
            url_path = parsed_url.path
            
            # Get the last part of the path
            filename = os.path.basename(url_path)
            
            # If there's no filename or it has no extension
            if not filename or '.' not in filename:
                # Try to derive from content type
                if headers and 'Content-Type' in headers:
                    content_type = headers['Content-Type'].split(';')[0].strip()
                    ext = {
                        'text/plain': '.txt',
                        'text/html': '.html',
                        'text/css': '.css',
                        'text/javascript': '.js',
                        'application/pdf': '.pdf',
                        'application/json': '.json',
                        'application/xml': '.xml',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'image/gif': '.gif',
                        'application/zip': '.zip'
                    }.get(content_type, '.bin')
                    
                    # Use a timestamp as filename
                    timestamp = int(time.time())
                    return f"download_{timestamp}{ext}"
            
            # Return the filename, or a default if all else fails
            return filename if filename else f"download_{int(time.time())}.bin"

        except Exception as e:
            raise PluginError(f"Error resolving filename from url: {e}", plugin_name=NetworkPlugin.__name__) from e
        
    @staticmethod
    @tool(
        categories=["web", "download"],
        requires_network=True
    )
    def try_resolve_filename_from_url(url: str) -> Dict[str, Any]:
        """
        Try to resolve a filename from a URL without downloading the file.
        
        Args:
            url: The URL to check
            
        Returns:
            Dictionary with resolved filename information
        """
        tool_message_print(f"Resolving filename from: {url}")
        
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Make a HEAD request to get headers
            headers = {'User-Agent': random.choice(NetworkPlugin.USER_AGENTS)}
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            
            # Get the resolved filename
            filename = NetworkPlugin.resolve_filename_from_url(url, response.headers)
            
            return {
                "success": True,
                "url": url,
                "resolved_filename": filename,
                "content_type": response.headers.get('Content-Type', 'unknown'),
                "content_length": response.headers.get('Content-Length', 'unknown')
            }
            
        except Exception as e:
            raise PluginError(f"Error resolving filename from url: {e}", plugin_name=NetworkPlugin.__name__) from e
