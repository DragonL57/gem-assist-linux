"""
Search plugin providing web search and related functionality.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class SearchPlugin(Plugin):
    """Plugin providing search operations."""
    
    @staticmethod
    @tool(
        categories=["search", "web"],
        requires_network=True,
        rate_limited=True
    )
    def web_search(query: str, num_results: int = 5, region: str = "wt-wt") -> List[Dict[str, Any]]:
        """
        Perform a web search using DuckDuckGo.
        
        Args:
            query: Search query
            num_results: Number of results to return (max 10)
            region: Region code for search results (default: worldwide)
            
        Returns:
            List of search results with title, url, and snippet
        """
        tool_message_print(f"Searching for: {query}")
        
        try:
            from duckduckgo_search import DDGS
            
            # Limit number of results to a reasonable range
            if num_results > 10:
                num_results = 10
            elif num_results < 1:
                num_results = 1
                
            # Perform search
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region=region, safesearch="moderate", max_results=num_results))
                
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
                
            # Print results summary
            tool_report_print(f"Found {len(formatted_results)} results for query: '{query}'")
            
            return formatted_results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    @staticmethod
    @tool(
        categories=["search", "reddit"],
        requires_network=True,
        rate_limited=True
    )
    def reddit_search(query: str, subreddit: str = None, sort: str = "relevance", time_filter: str = "all", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Reddit for posts matching the query.
        
        Args:
            query: Search query
            subreddit: Optional subreddit to search in (default: all)
            sort: Sort method (relevance, hot, top, new, comments)
            time_filter: Time range (all, day, week, month, year)
            limit: Maximum number of results (default: 5)
            
        Returns:
            List of Reddit posts matching the query
        """
        tool_message_print(f"Searching Reddit for: {query}")
        
        try:
            import praw
            import os
            
            # Get Reddit credentials
            reddit_id = os.environ.get("REDDIT_ID")
            reddit_secret = os.environ.get("REDDIT_SECRET")
            
            if not reddit_id or not reddit_secret:
                return [{"error": "Reddit API credentials are not configured"}]
                
            # Initialize Reddit API client
            reddit = praw.Reddit(
                client_id=reddit_id,
                client_secret=reddit_secret,
                user_agent="gem-assist:v0.1 (by u/gem_assist_bot)"
            )
            
            # Perform search
            if subreddit:
                search_results = reddit.subreddit(subreddit).search(
                    query, sort=sort, time_filter=time_filter, limit=limit
                )
            else:
                search_results = reddit.subreddit("all").search(
                    query, sort=sort, time_filter=time_filter, limit=limit
                )
                
            # Format results
            results = []
            for post in search_results:
                created_time = datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
                results.append({
                    "id": post.id,
                    "title": post.title,
                    "author": str(post.author),
                    "url": f"https://reddit.com{post.permalink}",
                    "subreddit": post.subreddit.display_name,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "created": created_time,
                    "selftext": post.selftext[:500] + ('...' if len(post.selftext) > 500 else '')
                })
                
            # Print results summary
            tool_report_print(f"Found {len(results)} Reddit posts for query: '{query}'")
            
            return results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    @staticmethod
    @tool(
        categories=["search", "reddit"],
        requires_network=True,
        rate_limited=True
    )
    def get_reddit_post(post_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Reddit post.
        
        Args:
            post_id: Reddit post ID
            
        Returns:
            Dictionary containing post information
        """
        tool_message_print(f"Getting Reddit post: {post_id}")
        
        try:
            import praw
            import os
            
            # Get Reddit credentials
            reddit_id = os.environ.get("REDDIT_ID")
            reddit_secret = os.environ.get("REDDIT_SECRET")
            
            if not reddit_id or not reddit_secret:
                return {"error": "Reddit API credentials are not configured"}
                
            # Initialize Reddit API client
            reddit = praw.Reddit(
                client_id=reddit_id,
                client_secret=reddit_secret,
                user_agent="gem-assist:v0.1 (by u/gem_assist_bot)"
            )
            
            # Get the post
            post = reddit.submission(id=post_id)
            
            # Format post data
            created_time = datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
            result = {
                "id": post.id,
                "title": post.title,
                "author": str(post.author),
                "url": f"https://reddit.com{post.permalink}",
                "subreddit": post.subreddit.display_name,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "created": created_time,
                "selftext": post.selftext,
                "is_self": post.is_self,
                "over_18": post.over_18
            }
            
            # Add external URL if it's a link post
            if not post.is_self:
                result["external_url"] = post.url
                
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    @tool(
        categories=["search", "reddit", "comments"],
        requires_network=True,
        rate_limited=True
    )
    def reddit_submission_comments(post_id: str, limit: int = 10, sort: str = "best") -> List[Dict[str, Any]]:
        """
        Get comments from a Reddit post.
        
        Args:
            post_id: Reddit post ID
            limit: Maximum number of top-level comments to retrieve
            sort: Sort method (best, top, new, controversial, old, qa)
            
        Returns:
            List of comments from the post
        """
        tool_message_print(f"Getting comments for Reddit post: {post_id}")
        
        try:
            import praw
            import os
            
            # Get Reddit credentials
            reddit_id = os.environ.get("REDDIT_ID")
            reddit_secret = os.environ.get("REDDIT_SECRET")
            
            if not reddit_id or not reddit_secret:
                return [{"error": "Reddit API credentials are not configured"}]
                
            # Initialize Reddit API client
            reddit = praw.Reddit(
                client_id=reddit_id,
                client_secret=reddit_secret,
                user_agent="gem-assist:v0.1 (by u/gem_assist_bot)"
            )
            
            # Get the post and comments
            post = reddit.submission(id=post_id)
            
            # Set sort order
            if sort:
                post.comment_sort = sort
                
            # Retrieve comments
            post.comments.replace_more(limit=0)  # Skip "load more comments" items
            top_level_comments = list(post.comments)[:limit]
            
            # Format comments
            results = []
            for comment in top_level_comments:
                if comment.author:  # Skip deleted comments
                    created_time = datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S')
                    results.append({
                        "id": comment.id,
                        "author": str(comment.author),
                        "body": comment.body,
                        "score": comment.score,
                        "created": created_time,
                        "is_submitter": comment.is_submitter  # True if comment author is post author
                    })
                    
            # Print results summary
            tool_report_print(f"Found {len(results)} comments for Reddit post: '{post.title}'")
            
            return results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    @staticmethod
    @tool(
        categories=["search", "tools"],
        requires_network=False
    )
    def find_tools(keyword: str = None, category: str = None) -> List[Dict[str, Any]]:
        """
        Find available tools by keyword or category.
        
        Args:
            keyword: Optional keyword to search in tool names and descriptions
            category: Optional category to filter tools by
            
        Returns:
            List of matching tools with their descriptions
        """
        from plugins import get_registry
        
        tool_message_print(f"Finding tools with keyword: '{keyword}', category: '{category}'")
        
        registry = get_registry()
        tools = registry.get_tools()
        
        results = []
        for name, func in tools.items():
            capabilities = registry.get_capabilities(name)
            
            # Filter by category if provided
            if category:
                tool_categories = capabilities.get("categories", [])
                if category.lower() not in [c.lower() for c in tool_categories]:
                    continue
            
            # Filter by keyword in name or description if provided
            if keyword:
                keyword_lower = keyword.lower()
                name_match = keyword_lower in name.lower()
                desc_match = keyword_lower in capabilities.get("description", "").lower()
                
                if not (name_match or desc_match):
                    continue
            
            # Get function signature
            import inspect
            signature = str(inspect.signature(func))
            
            # Add to results
            results.append({
                "name": name,
                "signature": f"{name}{signature}",
                "categories": capabilities.get("categories", []),
                "description": capabilities.get("description", ""),
                "requires_network": capabilities.get("requires_network", False),
                "requires_filesystem": capabilities.get("requires_filesystem", False),
                "rate_limited": capabilities.get("rate_limited", False),
            })
        
        # Sort by name
        results.sort(key=lambda x: x["name"])
        
        # Print results summary
        tool_report_print(f"Found {len(results)} matching tools")
        
        return results
