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

def duckduckgo_search_tool(query: str) -> list:
    """
    Searches DuckDuckGo for the given query and returns a list of results.

    Args:
        query: The search query.

    Returns:
        list: A list of search results.
    """
    tool_message_print("duckduckgo_search_tool", [("query", query)])
    try:
        ddgs = duckduckgo_search.DDGS(timeout=conf.DUCKDUCKGO_TIMEOUT)
        results = ddgs.text(query, max_results=conf.MAX_DUCKDUCKGO_SEARCH_RESULTS)
        return results
    except Exception as e:
        tool_report_print("Error during DuckDuckGo search:", str(e), is_error=True)
        return f"Error during DuckDuckGo search: {e}"

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
