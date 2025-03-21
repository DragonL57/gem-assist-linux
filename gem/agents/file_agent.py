"""
File system specialized agent.
"""
from typing import List, Callable, Dict, Any
from rich.console import Console
import os
import json

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
            get_current_directory, self.update_current_directory, self.resolve_path
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
        - Before performing operations, resolve all paths using the resolve_path tool
        - When navigating, use update_current_directory to maintain navigation context
        - If a file operation fails, check for permissions issues or if the path exists
        
        PATH RESOLUTION:
        - Always resolve relative paths to absolute paths before operations
        - Handle special paths like ~, ., and .. properly using resolve_path
        - For cross-platform compatibility, avoid hardcoded path separators
        
        ERROR HANDLING:
        - If an operation fails, try alternative approaches before giving up
        - Use request_assistance when you need help from other agents
        - Notify the orchestrator of any serious issues
        
        When finished with a task, always use complete_task to return your results.
        """
        
        super().__init__(
            name="FileSystem",
            model=model,
            tools=file_tools,
            system_instruction=system_instruction,
            console=console
        )
    
    def act(self, query: str, task_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process file system related tasks with appropriate guidance.
        """
        # Add context awareness specifically for file system operations
        current_dir = self.context.current_directory
        recent_files_info = ""
        
        if self.context.recent_files:
            recent_files = [f['path'] for f in self.context.recent_files[-3:]]
            recent_files_info = f"Recently accessed files: {', '.join(recent_files)}"
        
        # Provide guidance without hardcoding specific behavior
        enhanced_query = f"""Task: {query}
        
        Current directory: {current_dir}
        {recent_files_info}
        
        As you work on this file system task:
        1. First check the current directory and existing files when needed
        2. Ensure paths are valid before operations by using resolve_path
        3. Handle files with non-ASCII names or spaces properly
        4. Update the current directory context when navigating
        """
        
        return super().act(enhanced_query, task_context)
    
    def update_current_directory(self, new_directory: str) -> Dict[str, Any]:
        """
        Update the current directory in the global context.
        
        Args:
            new_directory: Path to the new directory
            
        Returns:
            Status of the directory change operation
        """
        resolved_path = self.resolve_path(new_directory)
        
        if not os.path.exists(resolved_path):
            return {
                "success": False,
                "message": f"Directory does not exist: {resolved_path}"
            }
        
        if not os.path.isdir(resolved_path):
            return {
                "success": False,
                "message": f"Path is not a directory: {resolved_path}"
            }
        
        # Update the context
        self.context.current_directory = resolved_path
        self.context.visited_directories.add(resolved_path)
        
        # Log the navigation operation
        self.context.track_operation(
            agent=self.name,
            operation="navigate",
            details={"directory": resolved_path},
            success=True
        )
        
        return {
            "success": True,
            "previous_directory": self.context.current_directory,
            "current_directory": resolved_path,
            "message": f"Changed directory to: {resolved_path}"
        }
    
    def resolve_path(self, path: str) -> str:
        """
        Resolve a relative path to an absolute path.
        
        Args:
            path: The path to resolve (can be absolute, relative, or contain ~)
            
        Returns:
            The resolved absolute path
        """
        # Handle home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
            
        # If already absolute, just normalize it
        if os.path.isabs(path):
            return os.path.normpath(path)
            
        # Otherwise, join with current directory and normalize
        abs_path = os.path.normpath(os.path.join(self.context.current_directory, path))
        return abs_path