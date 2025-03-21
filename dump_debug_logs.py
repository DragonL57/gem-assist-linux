#!/usr/bin/env python3
"""
Utility script to dump litellm debug logs when debugging an issue.
Run this after your model returns incomplete reasoning.
"""
import sys
import json
from rich.console import Console
from rich.syntax import Syntax

# Try to import litellm
try:
    import litellm
except ImportError:
    print("litellm not installed. Please install it with 'pip install litellm'.")
    sys.exit(1)

console = Console()

def dump_debug_logs():
    """Dump litellm debug logs"""
    if not hasattr(litellm, '_debug_log'):
        console.print("[bold red]No debug logs found.[/] Make sure you've run litellm._turn_on_debug() before making requests.")
        return
    
    console.print(f"[bold green]Found {len(litellm._debug_log)} debug log entries[/]")
    
    for i, log in enumerate(litellm._debug_log):
        console.print(f"\n[bold blue]Debug Log Entry #{i+1}[/]")
        
        # Check if the log entry has model reasoning
        if isinstance(log, dict) and 'model_reasoning' in log:
            console.print("[bold cyan]Model Reasoning:[/]")
            console.print(log['model_reasoning'])
        
        # Format and print the full log entry
        try:
            formatted_log = json.dumps(log, indent=2)
            syntax = Syntax(formatted_log, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        except (TypeError, ValueError):
            console.print(str(log))

if __name__ == "__main__":
    dump_debug_logs()
