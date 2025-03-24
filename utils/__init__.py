"""
Main utilities package that exports all tools.
This file collects and exports all tools from the various utility modules.
"""

# Import all tools from the various modules
from .core import (
    tool_message_print, tool_report_print
)
from .filesystem import (
    list_dir, get_drives, get_multiple_directory_size,
    create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory, read_file_content,
)
from .network import (
    get_website_text_content, http_get_request, http_post_request,
    open_url, download_file_from_url, resolve_filename_from_url,
    try_resolve_filename_from_url, get_youtube_transcript
)
from .system import (
    get_system_info, run_shell_command, get_current_datetime,
    evaluate_math_expression, get_environment_variable
)
from .search import (
    reddit_search, get_reddit_post,
    reddit_submission_comments, find_tools,
    web_search  # Renamed from filtered_search
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
    # File system tools
    list_dir, get_drives, get_multiple_directory_size,
    create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory, read_file_content,
    
    # Network tools
    get_website_text_content, http_get_request, http_post_request,
    open_url, download_file_from_url, get_youtube_transcript,
    
    # System tools
    get_system_info, run_shell_command, get_current_datetime,
    evaluate_math_expression, get_environment_variable,
    
    # Search tools
    reddit_search, get_reddit_post,
    reddit_submission_comments, find_tools,
    web_search,
    
    # Archive tools
    zip_archive_files, zip_extract_files,
    
    # Document tools
    convert_document, read_excel_file, read_excel_structure,
    read_pdf_text, convert_excel_to_format,
    
    # Web scraping tools
    extract_structured_data, extract_tables_to_dataframes,
    scrape_with_pagination, scrape_dynamic_content,
    
    # Code execution tools
    execute_python_code, analyze_pandas_dataframe
]

__all__ = [
    'tool_message_print', 'tool_report_print',
    'list_dir', 'get_drives', 'get_multiple_directory_size', 'create_directory', 
    'get_file_metadata', 'write_files', 'copy_file', 'move_file', 'rename_file', 'rename_directory', 'find_files', 
    'get_website_text_content', 'http_get_request', 'http_post_request', 'open_url', 'download_file_from_url', 
    'get_youtube_transcript',
    'get_system_info', 'run_shell_command', 'get_current_datetime', 'evaluate_math_expression', 'get_current_directory', 
    'zip_archive_files', 'zip_extract_files', 'get_environment_variable', 
    'find_tools', 'web_search',
    'reddit_search', 'get_reddit_post', 'reddit_submission_comments',
    'convert_document', 'read_excel_file', 'read_excel_structure', 'read_pdf_text', 'convert_excel_to_format', 
    'extract_structured_data', 'extract_tables_to_dataframes', 'scrape_with_pagination', 'scrape_dynamic_content', 
    'execute_python_code', 'analyze_pandas_dataframe', 'read_file_content'
]
