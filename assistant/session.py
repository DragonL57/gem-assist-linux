"""
Session management for the assistant.
"""
import os
import pickle
import asyncio
from typing import Dict, Any, List, Optional
from colorama import Fore, Style
from gem.command import cmd

class ChatSession:
    """Manages a chat session with the assistant."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        self.current_reasoning = None
        self.current_tool_calls = []
        self.current_tool_results = []
        self.processing = False
        self.stop_requested = False
        
    def clear(self):
        """Reset the session state."""
        self.current_reasoning = None
        self.current_tool_calls = []
        self.current_tool_results = []
        self.stop_requested = False
        
    def start_processing(self):
        """Mark session as processing."""
        self.processing = True
        self.stop_requested = False
        self.current_tool_calls = []
        self.current_tool_results = []
        
    def stop_processing(self):
        """Request processing to stop."""
        if self.processing:
            self.stop_requested = True
            return True
        return False
        
    def finish_processing(self):
        """Mark session as done processing."""
        self.processing = False
        self.stop_requested = False

class SessionManager:
    """Manages saving and loading of sessions."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        
    @cmd(["save"], "Saves the current chat session to pickle file.")
    async def save_session(self, name: str, filepath: str = "chats") -> None:
        """
        Save the current chat session to a file.
        
        Args:
            name: The name of the file to save the session to (without extension)
            filepath: The path to the directory to save the file to (default: "chats")
        """
        try:
            # create directory if default path doesn't exist
            if filepath == "chats":
                os.makedirs(filepath, exist_ok=True)

            final_path = os.path.join(filepath, name + ".pkl")
            
            # Run file operations in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_to_file, final_path, self.assistant.messages)

            print(
                f"{Fore.GREEN}Chat session saved to {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            
    def _save_to_file(self, path: str, data: Any) -> None:
        """Helper method to save data to a file."""
        with open(path, "wb") as f:
            pickle.dump(data, f)
            
    @cmd(["load"], "Loads a chat session from a pickle file. Resets the session.")
    async def load_session(self, name: str, filepath: str = "chats") -> None:
        """
        Load a chat session from a file.
        
        Args:
            name: The name of the file to load the session from (without extension)
            filepath: The path to the directory to load the file from (default: "chats")
        """
        try:
            final_path = os.path.join(filepath, name + ".pkl")
            
            # Run file operations in thread pool
            loop = asyncio.get_event_loop()
            self.assistant.messages = await loop.run_in_executor(None, self._load_from_file, final_path)
            
            print(
                f"{Fore.GREEN}Chat session loaded from {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except FileNotFoundError:
            print(
                f"{Fore.RED}Chat session not found{Style.RESET_ALL} {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            
    def _load_from_file(self, path: str) -> Any:
        """Helper method to load data from a file."""
        with open(path, "rb") as f:
            return pickle.load(f)
    
    @cmd(["reset"], "Resets the chat session but keeps the terminal display.")
    async def reset_session(self, force: bool = False) -> None:
        """
        Reset the chat session but keeps the system instruction if present.
        """
        old_length = len(self.assistant.messages)
        
        # Keep only the system instruction if present
        if self.assistant.system_instruction:
            self.assistant.messages = [{"role": "system", "content": self.assistant.system_instruction}]
        else:
            self.assistant.messages = []
        
        if self.assistant.system_instruction:
            self.assistant.messages.append({"role": "system", "content": self.assistant.system_instruction})
        
        # Clear reasoning history too
        self.assistant.last_reasoning = None
        
        # Announce the reset with visual distinction
        reset_message = "[bold green]✅ Conversation reset successfully![/]"
        self.assistant.console.print("\n" + reset_message + "\n")
        self.assistant.console.print(f"[dim]Cleared {old_length - (1 if self.assistant.system_instruction else 0)} messages.[/]")
        self.assistant.console.print("[dim]You can start a new conversation now.[/]\n")
