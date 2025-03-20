"""
File system specialized agent.
"""
from typing import List, Callable, Dict, Any
from rich.console import Console

from .base_agent import BaseAgent
from utils import (
    list_dir, get_drives, get_directory_size, get_multiple_directory_size,
    read_file, create_directory, get_file_metadata, write_files,
    copy_file, move_file, rename_file, rename_directory, find_files,
    get_current_directory
)

class FileSystemAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        console: Console = None
    ):
        # Collect all file-related tools
        file_tools = [
            list_dir, get_drives, get_directory_size, get_multiple_directory_size,
            read_file, create_directory, get_file_metadata, write_files,
            copy_file, move_file, rename_file, rename_directory, find_files,
            get_current_directory
        ]
        
        system_instruction = """
        You are a specialized file system agent that handles all operations related to files and directories.
        Your job is to:
        1. Help users navigate the file system
        2. Create, read, update, and delete files and directories
        3. Search for files and get information about them
        4. Perform operations like moving, copying, and renaming files
        
        FILE SYSTEM OPERATION GUIDELINES:
        - Always check the current directory first with get_current_directory()
        - For listing files, use list_dir() and specify files_only=True if only files are needed
        - For "documents folder", first determine the OS and user home directory
        - When listing files, provide formatting for readability (bullet points, table)
        - If a file operation fails, check for permissions issues or if the path exists
        
        Always verify paths exist before attempting operations on them.
        Be careful with destructive operations (deleting, overwriting).
        When working with file paths, ensure they are properly formatted for the current operating system.
        """
        
        super().__init__(
            name="FileSystem",
            model=model,
            tools=file_tools,
            system_instruction=system_instruction,
            console=console
        )
    
    def act(self, query: str) -> Dict[str, Any]:
        """
        Process file system related tasks with appropriate guidance.
        """
        # Provide guidance without hardcoding specific behavior
        enhanced_query = f"""Task: {query}
        
        As you work on this file system task:
        1. First check the current directory and existing files when needed
        2. Ensure paths are valid before operations
        3. Handle files with non-ASCII names or spaces properly
        
        Use appropriate file system tools to complete this task efficiently."""
        
        return super().act(enhanced_query)
