"""
Search utility functions for the gem-assist package.
These functions are used for searching the web, Reddit, and Wikipedia.
"""

import os
import duckduckgo_search
import praw
from praw.reddit import Comment
import wikipedia
import thefuzz.process
from dotenv import load_dotenv
from colorama import Fore, Style
from typing import Dict, List, Optional, Union
import re
from datetime import datetime, timedelta

from .core import tool_message_print, tool_report_print
import config as conf

# Load environment variables
load_dotenv()

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    user_agent="PersonalBot/1.0",
)

# Try to import Google Search API if available
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False

# Basic DuckDuckGo search tool removed - use advanced_duckduckgo_search instead

def advanced_duckduckgo_search(query: str, time_period: str = None, 
                              region: str = "wt-wt", safesearch: str = "moderate",
                              max_results: int = 10, domain: str = None) -> List[Dict]:
    """
    Performs an advanced DuckDuckGo search with filtering options.
    
    Args:
        query: Search query string
        time_period: Time filter (d: day, w: week, m: month, y: year)
        region: Region code for localized results, default is "wt-wt" (worldwide)
        safesearch: Safe search setting ("on", "moderate", "off")
        max_results: Maximum number of results to return
        domain: Filter results to a specific domain (e.g., "wikipedia.org")
        
    Returns:
        List of search results as dictionaries
    """
    tool_message_print("advanced_duckduckgo_search", [
        ("query", query),
        ("time_period", time_period or "all time"),
        ("region", region),
        ("safesearch", safesearch),
        ("max_results", str(max_results)),
        ("domain", domain or "any")
    ])
    
    try:
        # Modify query if domain filter is specified
        if domain:
            query = f"site:{domain} {query}"
        
        # Initialize DuckDuckGo search
        ddgs = duckduckgo_search.DDGS(timeout=conf.DUCKDUCKGO_TIMEOUT)
        
        # Set time period parameter
        time_map = {
            "d": "d",
            "day": "d",
            "w": "w",
            "week": "w",
            "m": "m",
            "month": "m",
            "y": "y",
            "year": "y"
        }
        time_param = time_map.get(time_period, "")
        
        # Convert safesearch parameter
        safesearch_map = {
            "on": "strict",
            "moderate": "moderate",
            "off": "off"
        }
        safesearch_param = safesearch_map.get(safesearch, "moderate")
        
        # Perform the search
        results = list(ddgs.text(
            query,
            region=region,
            safesearch=safesearch_param,
            timelimit=time_param,
            max_results=max_results
        ))
        
        tool_report_print("Advanced DuckDuckGo search complete:", f"Found {len(results)} results for '{query}'")
        return results
    
    except Exception as e:
        tool_report_print("Error during advanced DuckDuckGo search:", str(e), is_error=True)
        return [{"error": f"Search failed: {str(e)}"}]

def google_search(query: str, num_results: int = 10, language: str = "en", 
                country: str = "us", time_period: str = None, site_restrict: str = None) -> List[Dict]:
    """
    Perform a search using Google Custom Search API.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.
    
    Args:
        query: Search query
        num_results: Number of results to return (1-10)
        language: Language code for results
        country: Country code for results
        time_period: Time filter ("d": day, "w": week, "m": month, "y": year)
        site_restrict: Restrict results to specific domain
        
    Returns:
        List of search results
    """
    tool_message_print("google_search", [
        ("query", query),
        ("num_results", str(num_results)),
        ("language", language),
        ("country", country),
        ("time_period", time_period or "all time")
    ])
    
    if not GOOGLE_SEARCH_AVAILABLE:
        return [{"error": "Google Search API not available. Please install google-api-python-client"}]
    
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not google_api_key or not google_cse_id:
        return [{"error": "Google API key or Custom Search Engine ID not found in environment variables"}]
    
    try:
        # Build the service
        service = build("customsearch", "v1", developerKey=google_api_key)
        
        # Prepare search parameters
        search_params = {
            "q": query,
            "cx": google_cse_id,
            "num": min(num_results, 10),  # API limit is 10 results per request
            "hl": language,
            "gl": country
        }
        
        # Add site restriction if provided
        if site_restrict:
            search_params["siteSearch"] = site_restrict
        
        # Add date restriction if provided
        if time_period:
            date_restrict = None
            if time_period == "d":
                date_restrict = "d1"  # Last day
            elif time_period == "w":
                date_restrict = "w1"  # Last week
            elif time_period == "m":
                date_restrict = "m1"  # Last month
            elif time_period == "y":
                date_restrict = "y1"  # Last year
            
            if date_restrict:
                search_params["dateRestrict"] = date_restrict
        
        # Execute the search
        search_results = service.cse().list(**search_params).execute()
        
        # Process and return results
        results = []
        if "items" in search_results:
            for item in search_results["items"]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Google"
                })
        
        tool_report_print("Google search complete:", f"Found {len(results)} results for '{query}'")
        return results
    
    except HttpError as e:
        tool_report_print("Google Search API error:", str(e), is_error=True)
        return [{"error": f"API error: {str(e)}"}]
    
    except Exception as e:
        tool_report_print("Error during Google search:", str(e), is_error=True)
        return [{"error": f"Search failed: {str(e)}"}]

def meta_search(query: str, sources: List[str] = ["duckduckgo", "google", "wikipedia"], 
               max_results_per_source: int = 5) -> Dict[str, List]:
    """
    Perform a search across multiple search engines and aggregate results.
    
    Args:
        query: Search query
        sources: List of search engines to use ("duckduckgo", "google", "wikipedia")
        max_results_per_source: Maximum number of results per search engine
        
    Returns:
        Dictionary with results from each search engine
    """
    tool_message_print("meta_search", [
        ("query", query),
        ("sources", str(sources)),
        ("max_results_per_source", str(max_results_per_source))
    ])
    
    results = {}
    
    for source in sources:
        if source.lower() == "duckduckgo":
            results["duckduckgo"] = advanced_duckduckgo_search(
                query, 
                max_results=max_results_per_source
            )
        elif source.lower() == "google":
            results["google"] = google_search(
                query,
                num_results=max_results_per_source
            )
        elif source.lower() == "wikipedia":
            wiki_results = search_wikipedia(query)[:max_results_per_source]
            results["wikipedia"] = wiki_results
    
    # Count total results
    total_results = sum(len(results.get(source, [])) for source in sources)
    tool_report_print("Meta search complete:", f"Found {total_results} results across {len(sources)} sources")
    
    return results

def reddit_search(subreddit: str, sorting: str, query: str | None = None) -> dict:
    """
    Search inside `all` or specific subreddit in reddit to get information.
    
    This function CAN also work WITHOUT a query with just sorting of specific subreddit/s
    just provide the sorting from one of these ['hot', 'top', 'new'] and leave query as empty string

    Args:
        query: The query string to search for, leave as empty string if you are looking for specific sorting like "new" or "hot" all
        subreddit: The name of the subreddit or 'all' to get everyhing, subreddit names can be mixed for example 'Python+anime+cpp' which could combine them. for global search use 'all'
        sorting: the sorting of the post, can be 'relevance', 'hot', 'top', 'new' or 'comments', use 'top' as default
    
    Example: `reddit_search("AI")`

    Returns: A list of JSON data with information containing submission_id, title, text (if any), number of comments, name of subreddit, upvote_ratio, url   
    """
    tool_message_print("reddit_search", [("query", query), ("subreddit", subreddit), ("sorting", sorting)])
    if sorting not in ('relevance', 'hot', 'top', 'new', 'comments'):
        print(f"{Fore.RED}Failed to search reddit: invalid sorting {Style.RESET_ALL}")
        return "Invalid sorting, must contain either of these: 'relevance', 'hot', 'top', 'new' or 'comments'"

    results = []
    subs = []
    max_results = conf.MAX_REDDIT_SEARCH_RESULTS
    if query:
        subs = reddit.subreddit(subreddit).search(query, limit=max_results, sort=sorting)
    else:
        match sorting:
            case "new":
                subs = reddit.subreddit(subreddit).new(limit=max_results)
            case "hot":
                subs = reddit.subreddit(subreddit).hot(limit=max_results)
            case "top":
                subs = reddit.subreddit(subreddit).top(limit=max_results)
            case _:
                subs = reddit.subreddit(subreddit).top(limit=max_results)

    for s in subs:
        sub_id = "N/A"
        if s.name:
            sub_id = s.name.replace("t3_", "")
        results.append({
            "submission_id": sub_id,
            "title": s.title or "N/A",
            "text": (s.selftext if s.is_self else s.url) or "N/A",
            "num_comments": s.num_comments,
            "subreddit_name": s.subreddit.display_name or "N/A",
            "upvote_ratio": s.upvote_ratio or "N/A"
        })

    tool_report_print("Fetched:", f"{len(results)} reddit results.")
    return results

def get_reddit_post(submission_id: str) -> dict:
    """Get contents like text title, number of comments subreddit name of a specific 
    reddit post.
    This does not include comments, just send in the submission id, dont ask the user for it, if they give it use it otherwise use contents of search

    Args:
        submission_url: the submission id of the reddit post

    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """
    tool_message_print("get_reddit_post", [("submission_id", submission_id)])

    try:
        s = reddit.submission(submission_id)
        if not s:
            return "Submission not found/Invalid ID"

        sub_id = "N/A"
        if s.name:
            sub_id = s.name.replace("t3_", "")

        result = {
            "submission_id": sub_id,
            "title": s.title or "N/A",
            "text": (s.selftext if s.is_self else s.url) or "N/A",
            "num_comments": s.num_comments,
            "subreddit_name": s.subreddit.display_name or "N/A",
            "upvote_ratio": s.upvote_ratio or "N/A"
        }
    except Exception as e:
        tool_report_print("Error getting reddit post:", str(e), is_error=True)
        return f"Error getting reddit post: {e}"
        
    return result

def reddit_submission_comments(submission_url: str) -> dict: 
    """
    Get a compiled list of comments of a specific reddit post
    For finding solutions for a problem, solutions are usually in the comments, so this will be helpful for that
    (Might not include all comments)

    Args:
        submission_url: the submission url of the reddit post

    Returns: A JSON data of the comments including authors name and the body of the reddit post
    """
    tool_message_print("reddit_submission_comments", [("submission_url", submission_url)])

    submission = reddit.submission(submission_url)
    if not submission:
        return "Submission not found/Invalid ID"

    results = []
    comments = submission.comments.list() if conf.MAX_REDDIT_POST_COMMENTS == -1 else submission.comments.list()[:conf.MAX_REDDIT_POST_COMMENTS]
    for com in comments:
        if isinstance(com, Comment):
            results.append({
                "author": com.author.name if hasattr(com.author, 'name') else "N/A",
                "body": com.body or "N/A"
            })
    
    print(f"{Fore.CYAN}  ├─Fetched {len(results)} reddit comments.")
    return results

def get_wikipedia_summary(page: str) -> str:
    """
    Get a quick summery of a specific Wikipedia page, page must be a valid page name (not case sensitive)

    Args:
        page: the page name of the Wikipedia page (can be url too)

    Returns: A summary of the Wikipedia page
    """
    tool_message_print("get_wikipedia_summary", [("page", page)])
    try:
        if page.startswith("https"):
            page = page.split("wiki/")[1]
        return wikipedia.summary(page)
    except Exception as e:
        tool_report_print("Error getting Wikipedia summary:", str(e), is_error=True)
        return f"Error getting Wikipedia summary: {e}"

def search_wikipedia(query: str) -> list:
    """
    Search Wikipedia for a given query and return a list of search results, which can be used to get summery or full page conent

    Args:
        query: the search query

    Returns: A list of Wikipedia search results
    """
    tool_message_print("search_wikipedia", [("query", query)])
    try:
        return wikipedia.search(query)
    except Exception as e:
        tool_report_print("Error searching Wikipedia:", str(e), is_error=True)
        return f"Error searching Wikipedia: {e}"

def get_full_wikipedia_page(page: str) -> str:
    """
    Get the full content of a Wikipedia page, page must be a valid page name (not case sensitive)
    Use get_wikipedia_summary if you want a quick summery, and use this to get full page of any wikipedia, do not use get_website_text_content for wikipeida

    Args:
        page: the page name of the Wikipedia page (can be url too)

    Returns: A full Wikipedia page
    """
    tool_message_print("get_full_wikipedia_page", [("page", page)])
    try:
        if page.startswith("https"):
            page = page.split("wiki/")[1]
        page = wikipedia.page(page)
        content = f"Title: {page.title}\nUrl:{page.url}\n{page.content}"
        return content
    except Exception as e:
        tool_report_print("Error getting Wikipedia page:", str(e), is_error=True)
        return f"Error getting Wikipedia page: {e}"

def find_tools(query: str) -> list[str]:
    """
    Allows the assistant to find tools that fuzzy matchs a given query. 
    Use this when you are not sure if a tool exists or not, it is a fuzzy search.

    Args:
        query: The search query.

    Returns:
        A list of tool names and doc that match the query.
    """
    # Change relative import to absolute import
    from utils import TOOLS  # Changed from ..__init__ import TOOLS
    
    tool_message_print("find_tools", [("query", query)])
    tools = [tool.__name__ for tool in TOOLS]
    best_matchs = thefuzz.process.extractBests(query, tools) # [(tool_name, score), ...]
    return [
        [match[0], next((tool.__doc__.strip() for tool in TOOLS if tool.__name__ == match[0]), None)]
        for match in best_matchs
        if match[1] > 60 # only return tools with a score above 60
    ]

def filtered_search(
    query: str, 
    time_period: str = None,
    content_type: str = None, 
    site_restrict: str = None,
    exclude_terms: str = None,
    min_results: int = 5,
    max_results: int = 15,
    sort_by: str = "relevance"
) -> List[Dict]:
    """
    Perform an advanced search with comprehensive filtering and ranking options.
    
    Args:
        query: Main search query
        time_period: Time restriction (d: day, w: week, m: month, y: year)
        content_type: Filter by content type (news, blogs, academic, videos)
        site_restrict: Limit search to specific domains (e.g., "wikipedia.org")
        exclude_terms: Terms to exclude from search results (comma-separated)
        min_results: Minimum number of results to return
        max_results: Maximum number of results to return
        sort_by: How to rank results (relevance, date, authority)
        
    Returns:
        Filtered and ranked list of search results
    """
    tool_message_print("filtered_search", [
        ("query", query),
        ("time_period", time_period or "all time"),
        ("content_type", content_type or "all"),
        ("site_restrict", site_restrict or "all sites"),
        ("exclude_terms", exclude_terms or "none"),
        ("sort_by", sort_by)
    ])
    
    try:
        # Build the enhanced query with filters
        enhanced_query = query
        
        # Add site restriction
        if site_restrict:
            enhanced_query = f"site:{site_restrict} {enhanced_query}"
        
        # Add content type filter
        if content_type:
            content_filters = {
                "news": "inurl:news OR inurl:article",
                "blogs": "inurl:blog",
                "academic": "filetype:pdf OR site:.edu OR site:.gov OR site:scholar.google.com",
                "videos": "site:youtube.com OR site:vimeo.com"
            }
            if content_type.lower() in content_filters:
                enhanced_query = f"{enhanced_query} {content_filters[content_type.lower()]}"
        
        # Add excluded terms
        if exclude_terms:
            excluded = [f"-{term.strip()}" for term in exclude_terms.split(",")]
            enhanced_query = f"{enhanced_query} {' '.join(excluded)}"
        
        # Initialize search
        ddgs = duckduckgo_search.DDGS()
        
        # Set time period parameter
        time_map = {
            "d": "d", "day": "d", "w": "w", "week": "w", 
            "m": "m", "month": "m", "y": "y", "year": "y"
        }
        time_param = time_map.get(time_period, "") if time_period else ""
        
        # Perform the search
        raw_results = list(ddgs.text(
            enhanced_query,
            timelimit=time_param,
            max_results=max(max_results * 2, 20)  # Get more results than needed for better filtering
        ))
        
        # Rerank results based on sort_by parameter
        if sort_by.lower() == "date" and raw_results:
            # Simple attempt to prioritize results with dates in the title/body
            raw_results.sort(key=lambda x: sum(term in x.get('title', '').lower() + x.get('body', '').lower() 
                                          for term in ['2023', '2024', 'today', 'latest', 'new', 'update']), 
                         reverse=True)
        elif sort_by.lower() == "authority" and raw_results:
            # Simple heuristic for "authority" - prioritize known domains
            authority_domains = ['.edu', '.gov', '.org', 'wikipedia.org', 'github.com', 'stackoverflow.com']
            raw_results.sort(key=lambda x: sum(domain in x.get('href', '').lower() for domain in authority_domains), 
                         reverse=True)
        
        # Return sorted and limited results
        results = raw_results[:max_results]
        
        tool_report_print("Filtered search complete:", 
                         f"Found {len(results)} results for '{query}' with filters applied")
        return results
    
    except Exception as e:
        tool_report_print("Error during filtered search:", str(e), is_error=True)
        return [{"error": f"Search failed: {str(e)}"}]
