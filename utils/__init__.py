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
    get_current_directory, read_file_content
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
    search_wikipedia, get_full_wikipedia_page, find_tools,
    # New advanced search tools
    advanced_duckduckgo_search, google_search, meta_search
)
from .archive import zip_archive_files, zip_extract_files

# Import the new document tools
from .document_utils import (
    convert_document, read_excel_file, read_excel_structure,
    read_pdf_text, convert_excel_to_format
)

# Import the new web scraping tools
from .web_scraper import (
    extract_structured_data, extract_tables_to_dataframes,
    scrape_with_pagination, scrape_dynamic_content
)

# Import the code execution tools
from .code_execution import (
    execute_python_code, analyze_pandas_dataframe
)

# Export tools list for the assistant to use
TOOLS = [
    # Core tools
    write_note, read_note,
    
    # File system tools
    list_dir, get_drives, get_directory_size, get_multiple_directory_size,
    read_file, create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory, read_file_content,
    
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
    advanced_duckduckgo_search, google_search, meta_search,
    
    # Archive tools
    zip_archive_files, zip_extract_files,
    
    # Document tools (new)
    convert_document, read_excel_file, read_excel_structure,
    read_pdf_text, convert_excel_to_format,
    
    # Web scraping tools (new)
    extract_structured_data, extract_tables_to_dataframes,
    scrape_with_pagination, scrape_dynamic_content,
    
    # Code execution tools (new)
    execute_python_code, analyze_pandas_dataframe
]

__all__ = [
    'tool_message_print', 'tool_report_print',
    'TOOLS',
    # Include all tool names for direct import
    'duckduckgo_search_tool', 'reddit_search', 'get_reddit_post', 'reddit_submission_comments',
    'write_note', 'read_note', 'list_dir', 'get_drives', 'get_directory_size',
    'get_multiple_directory_size', 'read_file', 'create_directory', 'get_file_metadata',
    'write_files', 'copy_file', 'move_file', 'rename_file', 'rename_directory',
    'find_files', 'get_website_text_content', 'http_get_request', 'http_post_request',
    'open_url', 'download_file_from_url', 'get_system_info', 'run_shell_command',
    'get_current_datetime', 'evaluate_math_expression', 'get_current_directory',
    'zip_archive_files', 'zip_extract_files', 'get_environment_variable',
    'get_wikipedia_summary', 'search_wikipedia', 'get_full_wikipedia_page', 'find_tools',
    # New tools
    'advanced_duckduckgo_search', 'google_search', 'meta_search',
    'convert_document', 'read_excel_file', 'read_excel_structure', 'read_pdf_text', 'convert_excel_to_format',
    'extract_structured_data', 'extract_tables_to_dataframes', 'scrape_with_pagination', 'scrape_dynamic_content',
    'execute_python_code', 'analyze_pandas_dataframe', 'read_file_content'
]
