"""
Main utilities package that exports all tools.
This file collects and exports all tools from the various utility modules.
"""

# Import all tools from the various modules
from .core import tool_message_print, tool_report_print, write_note, read_note
from .filesystem import (
    list_dir, get_drives, get_directory_size, get_multiple_directory_size,
    read_file, create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory
)
from .network import (
    get_website_text_content, http_get_request, http_post_request,
    open_url, download_file_from_url, resolve_filename_from_url,
    try_resolve_filename_from_url
)
from .system import (
    get_system_info, run_shell_command, get_current_datetime,
    evaluate_math_expression, get_environment_variable
)
from .search import (
    duckduckgo_search_tool, reddit_search, get_reddit_post,
    reddit_submission_comments, get_wikipedia_summary,
    search_wikipedia, get_full_wikipedia_page, find_tools
)
from .archive import zip_archive_files, zip_extract_files

# Export tools list for the assistant to use
TOOLS = [
    # Core tools
    write_note, read_note,
    
    # File system tools
    list_dir, get_drives, get_directory_size, get_multiple_directory_size,
    read_file, create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory,
    
    # Network tools
    get_website_text_content, http_get_request, http_post_request,
    open_url, download_file_from_url,
    
    # System tools
    get_system_info, run_shell_command, get_current_datetime,
    evaluate_math_expression, get_environment_variable,
    
    # Search tools
    duckduckgo_search_tool, reddit_search, get_reddit_post,
    reddit_submission_comments, get_wikipedia_summary,
    search_wikipedia, get_full_wikipedia_page, find_tools,
    
    # Archive tools
    zip_archive_files, zip_extract_files,
]

__all__ = [
    'tool_message_print', 'tool_report_print',
    'TOOLS',
    'duckduckgo_search_tool', 'reddit_search', 'get_reddit_post', 'reddit_submission_comments',
    'write_note', 'read_note', 'list_dir', 'get_drives', 'get_directory_size',
    'get_multiple_directory_size', 'read_file', 'create_directory', 'get_file_metadata',
    'write_files', 'copy_file', 'move_file', 'rename_file', 'rename_directory',
    'find_files', 'get_website_text_content', 'http_get_request', 'http_post_request',
    'open_url', 'download_file_from_url', 'get_system_info', 'run_shell_command',
    'get_current_datetime', 'evaluate_math_expression', 'get_current_directory',
    'zip_archive_files', 'zip_extract_files', 'get_environment_variable',
    'get_wikipedia_summary', 'search_wikipedia', 'get_full_wikipedia_page', 'find_tools',
]
