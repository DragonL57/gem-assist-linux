"""
Core utility functions for the gem-assist package.
These functions are used across the various tools modules.
"""

import os
import time
import colorama
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.markdown import Markdown
from rich.table import Table
from rich.box import ROUNDED
import json
import datetime
import re

# Initialize colorama
colorama.init(autoreset=True)

# Create a Rich console with a custom theme
theme = Theme({
    "tool": "cyan",
    "arg_name": "yellow",
    "arg_value": "bright_white",
    "success": "green",
    "error": "bold red",
    "warning": "yellow",
    "info": "blue"
})

console = Console(theme=theme)

def tool_message_print(msg: str, args: list[tuple[str, str]] = None):
    """Print a formatted tool message with enhanced visibility."""
    console = Console()
    
    # Create a more detailed and visually distinct title
    title = Text("🔧 TOOL EXECUTION", style="bold cyan")
    
    content = []
    content.append(Text(f"Tool: ", style="cyan bold") + Text(msg, style="white bold"))
    
    if args:
        args_text = Text("\nArguments:", style="cyan")
        content.append(args_text)
        
        # Create a more structured arguments display
        for arg_name, arg_value in args:
            arg_text = Text()
            arg_text.append(f"  • {arg_name}: ", style="cyan")
            
            # Format the value based on its length
            if isinstance(arg_value, str) and len(arg_value) > 100:
                display_value = arg_value[:97] + "..."
            else:
                display_value = str(arg_value)
                
            arg_text.append(display_value)
            content.append(arg_text)
    
    panel = Panel(
        "\n".join(str(item) for item in content),
        title=title,
        border_style="cyan",
        expand=False
    )
    console.print(panel)

def tool_report_print(msg: str, value: str, is_error: bool = False, execution_time: float = None):
    """Print a formatted tool result with enhanced details."""
    console = Console()
    
    # Create a more informative title with emoji
    emoji = "❌" if is_error else "✅"
    title = Text(f"{emoji} TOOL RESULT", style="bold red" if is_error else "bold green")
    
    content = []
    
    # Add the main message and value
    main_text = Text()
    main_text.append(f"{msg} ", style="bold")
    main_text.append(value, style="red" if is_error else None)
    content.append(main_text)
    
    # Add execution time if provided
    if execution_time is not None:
        time_text = Text(f"\nExecution time: {execution_time:.4f} seconds", style="dim")
        content.append(time_text)
    
    panel = Panel(
        "\n".join(str(item) for item in content),
        title=title,
        border_style="red" if is_error else "green",
        expand=False
    )
    console.print(panel)

# Memory file path - where user-specific memory is stored
MEMORY_FILE = "./assistant_memory.json"

def read_memory(topic: str = None) -> dict:
    """
    Read the assistant's memory about the user, optionally filtered by topic.
    
    Args:
        topic: Optional topic to filter memory by (e.g., "preferences", "background", "recent_activities")
        
    Returns:
        Dictionary containing memory entries, or specific topic memory if requested
    """
    tool_message_print("read_memory", [("topic", topic or "all")])
    
    try:
        # Create memory file with default structure if it doesn't exist
        if not os.path.exists(MEMORY_FILE):
            default_memory = {
                "meta": {
                    "created": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                },
                "preferences": {},
                "background": {},
                "recent_activities": {},
                "interests": {},
                "behavior_patterns": {},
                "custom_topics": {}
            }
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(default_memory, f, indent=2)
            memory = default_memory
        else:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
        
        # Return specific topic if requested, otherwise return all memory
        if topic:
            if topic in memory:
                tool_report_print("Memory retrieved:", f"Retrieved {len(memory[topic])} entries for topic '{topic}'")
                return {topic: memory[topic]}
            else:
                tool_report_print("Warning:", f"Topic '{topic}' not found in memory", is_error=True)
                return {"error": f"Topic '{topic}' not found in memory"}
        else:
            # Count total memory entries
            entry_count = sum(len(entries) if isinstance(entries, dict) else 1 
                             for key, entries in memory.items() 
                             if key != "meta")
            tool_report_print("Memory retrieved:", f"Retrieved all memory containing {entry_count} entries")
            return memory
    except Exception as e:
        tool_report_print("Error reading memory:", str(e), is_error=True)
        return {"error": f"Error reading memory: {str(e)}"}

def update_memory(topic: str, key: str, value: str, importance: int = 3) -> bool:
    """
    Update the assistant's memory about the user.
    
    Args:
        topic: The topic for this memory (e.g., "preferences", "background", "interests")
        key: The specific aspect being recorded (e.g., "favorite_color", "job", "hobbies")
        value: The value to store
        importance: Importance rating from 1-5, where 5 is most important
        
    Returns:
        Boolean indicating success or failure
    """
    tool_message_print("update_memory", [
        ("topic", topic),
        ("key", key),
        ("value_length", str(len(value))),
        ("importance", str(importance))
    ])
    
    try:
        # Read existing memory
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
        else:
            memory = {
                "meta": {
                    "created": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                },
                "preferences": {},
                "background": {},
                "recent_activities": {},
                "interests": {},
                "behavior_patterns": {},
                "custom_topics": {}
            }
        
        # Create topic if it doesn't exist
        if topic not in memory:
            memory[topic] = {}
            console.print(f"[bold yellow]Created new topic:[/] [cyan]{topic}[/]")
        
        # Check if this is an update to existing memory or new entry
        is_new = key not in memory[topic]
        old_value = None
        old_importance = None
        
        if not is_new:
            # This is an update - record old values for comparison
            old_value = memory[topic][key].get("value")
            old_importance = memory[topic][key].get("importance")
        
        # Update the memory
        memory[topic][key] = {
            "value": value,
            "importance": importance,
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        # Update metadata
        memory["meta"]["last_updated"] = datetime.datetime.now().isoformat()
        
        # Save updated memory
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
        
        # Show beautiful diff output with what changed
        if is_new:
            # New entry
            console.print(f"[bold green]✅ Added new memory:[/] [cyan]{topic}/{key}[/]")
            console.print(f"   [dim]Value:[/] [yellow]\"{value}\"[/]")
            console.print(f"   [dim]Importance:[/] [yellow]{importance}/5[/]")
        else:
            # Updated entry
            console.print(f"[bold blue]🔄 Updated memory:[/] [cyan]{topic}/{key}[/]")
            
            # Show value change if different
            if old_value != value:
                console.print(f"   [dim]Value:[/] [red]\"{old_value}\"[/] → [green]\"{value}\"[/]")
            else:
                console.print(f"   [dim]Value:[/] [yellow]\"{value}\"[/] [dim](unchanged)[/]")
            
            # Show importance change if different
            if old_importance != importance:
                console.print(f"   [dim]Importance:[/] [red]{old_importance}/5[/] → [green]{importance}/5[/]")
            else:
                console.print(f"   [dim]Importance:[/] [yellow]{importance}/5[/] [dim](unchanged)[/]")
        
        tool_report_print("Memory updated:", f"Successfully updated memory for {topic}/{key}")
        return True
    except Exception as e:
        tool_report_print("Error updating memory:", str(e), is_error=True)
        return False

def remove_memory(topic: str, key: str) -> bool:
    """
    Remove an item from the assistant's memory.
    
    Args:
        topic: The topic containing the memory item
        key: The key of the memory item to remove
        
    Returns:
        Boolean indicating success or failure
    """
    tool_message_print("remove_memory", [
        ("topic", topic),
        ("key", key)
    ])
    
    try:
        # Read existing memory
        if not os.path.exists(MEMORY_FILE):
            tool_report_print("Warning:", "Memory file does not exist", is_error=True)
            return False
            
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memory = json.load(f)
        
        # Check if topic exists
        if topic not in memory:
            tool_report_print("Warning:", f"Topic '{topic}' not found in memory", is_error=True)
            return False
            
        # Check if key exists in topic
        if key not in memory[topic]:
            tool_report_print("Warning:", f"Key '{key}' not found in topic '{topic}'", is_error=True)
            return False
            
        # Store the value being removed for display
        removed_value = memory[topic][key].get("value", "")
        removed_importance = memory[topic][key].get("importance", 0)
        
        # Remove the memory item
        del memory[topic][key]
        
        # Update metadata
        memory["meta"]["last_updated"] = datetime.datetime.now().isoformat()
        
        # Clean up empty topics
        if not memory[topic]:
            del memory[topic]
            console.print(f"[bold yellow]Removed empty topic:[/] [cyan]{topic}[/]")
        
        # Save updated memory
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
        
        # Show what was removed
        console.print(f"[bold red]🗑️ Removed memory:[/] [cyan]{topic}/{key}[/]")
        console.print(f"   [dim]Removed value:[/] [red]\"{removed_value}\"[/]")
        console.print(f"   [dim]Importance was:[/] [red]{removed_importance}/5[/]")
        
        tool_report_print("Memory removed:", f"Successfully removed memory item {topic}/{key}")
        return True
    except Exception as e:
        tool_report_print("Error removing memory:", str(e), is_error=True)
        return False

def summarize_memory() -> str:
    """
    Create a concise summary of the most important information in memory.
    
    Returns:
        String containing a summary of key user information based on importance
    """
    tool_message_print("summarize_memory", [])
    
    try:
        if not os.path.exists(MEMORY_FILE):
            tool_report_print("Warning:", "No memory file found", is_error=True)
            return "No memory information available yet."
        
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memory = json.load(f)
        
        summary_parts = ["# User Memory Summary"]
        
        # Process each topic
        for topic, items in memory.items():
            if topic == "meta":  # Skip metadata
                continue
                
            if not items:  # Skip empty topics
                continue
            
            # Find important items (importance >= 4)
            important_items = {k: v for k, v in items.items() 
                              if isinstance(v, dict) and v.get("importance", 0) >= 4}
            
            # Only include topics with important items
            if important_items:
                summary_parts.append(f"\n## {topic.title()}")
                for key, details in important_items.items():
                    value = details.get("value", "")
                    summary_parts.append(f"- {key}: {value}")
        
        if len(summary_parts) <= 1:
            summary_parts.append("\nNo significant memory entries found.")
            
        tool_report_print("Memory summarized:", "Created summary of key user information")
        return "\n".join(summary_parts)
    except Exception as e:
        tool_report_print("Error summarizing memory:", str(e), is_error=True)
        return f"Error summarizing memory: {str(e)}"

def analyze_user_input(user_input: str, detect_preferences: bool = True) -> dict:
    """
    Analyze user input to automatically extract potential memory items.
    This helps build memory passively during conversations.
    
    Args:
        user_input: The user's message to analyze
        detect_preferences: Whether to detect preferences from the input
        
    Returns:
        Dictionary with potential memory items identified
    """
    tool_message_print("analyze_user_input", [
        ("input_length", str(len(user_input))),
        ("detect_preferences", str(detect_preferences))
    ])
    
    # Pattern matching for common preference statements
    preference_patterns = [
        (r"(?:I|i) (?:like|love|enjoy|prefer) ([\w\s]+)", "likes"),
        (r"(?:I|i) (?:dislike|hate|don't like|do not like) ([\w\s]+)", "dislikes"),
        (r"(?:My|my) favorite (\w+) (?:is|are) ([\w\s]+)", "favorites"),
        (r"(?:I|i) (?:want|need) ([\w\s]+)", "wants_needs")
    ]
    
    # Personal information patterns
    personal_patterns = [
        (r"(?:I|i) (?:work as|am) (?:an?|the) ([\w\s]+)", "occupation"),
        (r"(?:I|i) live in ([\w\s,]+)", "location"),
        (r"(?:I|i) have (\d+) ([\w\s]+)", "possessions"),
        (r"(?:My|my) name is ([\w\s]+)", "name")
    ]
    
    extracted_info = {
        "preferences": {},
        "personal_info": {},
        "topics_of_interest": []
    }
    
    if detect_preferences:
        # Extract preferences
        for pattern, category in preference_patterns:
            matches = re.findall(pattern, user_input)
            if matches:
                extracted_info["preferences"][category] = matches
        
        # Extract personal information
        for pattern, category in personal_patterns:
            matches = re.findall(pattern, user_input)
            if matches:
                extracted_info["personal_info"][category] = matches[0] if isinstance(matches[0], str) else matches[0][0]
    
    # Extract potential topics of interest based on nouns
    try:
        import nltk
        from nltk.tag import pos_tag
        from nltk.tokenize import word_tokenize
        
        try:
            # Make sure we have the required NLTK data
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        
        tokens = word_tokenize(user_input)
        tagged = pos_tag(tokens)
        
        # Extract nouns (NN, NNS, NNP, NNPS)
        nouns = [word for word, tag in tagged if tag.startswith('NN') and len(word) > 3]
        if nouns:
            extracted_info["topics_of_interest"] = list(set(nouns))
    except ImportError:
        # NLTK not available, use simplified approach
        common_topics = ["technology", "science", "art", "music", "food", "travel", 
                        "books", "movies", "sports", "health", "finance", "education"]
        
        found_topics = [topic for topic in common_topics if topic.lower() in user_input.lower()]
        if found_topics:
            extracted_info["topics_of_interest"] = found_topics
    
    # Remove empty categories
    for category in list(extracted_info.keys()):
        if not extracted_info[category]:
            del extracted_info[category]
    
    tool_report_print("Input analyzed:", 
                     f"Identified {len(extracted_info.get('preferences', {}))} preferences and {len(extracted_info.get('topics_of_interest', []))} topics")
    return extracted_info

# Legacy functions maintained for backward compatibility
def write_note(content: str) -> str:
    """
    Legacy function that writes a note to the memory file under 'notes' topic.
    
    Args:
        content: The note content to write
        
    Returns:
        Status message
    """
    success = update_memory("notes", f"note_{int(time.time())}", content, importance=3)
    return "Note saved successfully" if success else "Failed to save note"

def read_note() -> str:
    """
    Legacy function that reads all notes from memory.
    
    Returns:
        String containing all notes
    """
    memory = read_memory("notes")
    
    if "notes" in memory:
        notes = memory["notes"]
        if notes:
            return "\n\n---\n\n".join([f"{datetime.datetime.fromisoformat(item['last_updated']).strftime('%Y-%m-%d %H:%M:%S')}\n{item['value']}" 
                                     for item in notes.values()])
        else:
            return "No notes found."
    else:
        return "No notes found."
