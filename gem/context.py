"""
Universal Context Management for the gem-assist multi-agent system.
This module provides context tracking and sharing capabilities across all agents.
"""

import os
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

class AgentContext:
    """Manages shared context between agents in the system."""
    
    def __init__(self):
        # Conversation and task tracking
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None
        self.completed_tasks: List[Dict[str, Any]] = []
        
        # File system navigation context
        self.current_directory: str = os.getcwd()
        self.visited_directories: Set[str] = {self.current_directory}
        self.recent_files: List[Dict[str, Any]] = []  # {path, operation, timestamp}
        
        # Operation tracking
        self.operations_log: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Entity recognition and reference tracking
        self.referenced_entities: Dict[str, Any] = {}
        
        # Temporary storage for agent-to-agent communication
        self.shared_data: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, agent: str = None) -> None:
        """Add a message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if agent:
            message["agent"] = agent
            
        self.conversation_history.append(message)
    
    def track_operation(self, agent: str, operation: str, details: Dict[str, Any], success: bool) -> None:
        """Track an operation performed by an agent."""
        log_entry = {
            "agent": agent,
            "operation": operation,
            "details": details,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        self.operations_log.append(log_entry)
        
        # If file operation, track in recent files
        if "file_path" in details:
            self.recent_files.append({
                "path": details["file_path"],
                "operation": operation,
                "timestamp": datetime.now().isoformat()
            })
            
        # If directory navigation, update tracking
        if operation == "navigate" and "directory" in details:
            self.current_directory = details["directory"]
            self.visited_directories.add(self.current_directory)
    
    def log_error(self, agent: str, operation: str, details: Dict[str, Any], error_message: str) -> None:
        """Log an error that occurred during an operation."""
        error_entry = {
            "agent": agent,
            "operation": operation,
            "details": details,
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }
        self.errors.append(error_entry)
        self.track_operation(agent, operation, details, False)
    
    def update_entity_reference(self, entity_type: str, identifier: str, data: Any) -> None:
        """Track a referenced entity for future queries."""
        if entity_type not in self.referenced_entities:
            self.referenced_entities[entity_type] = {}
            
        self.referenced_entities[entity_type][identifier] = {
            "data": data,
            "last_referenced": datetime.now().isoformat()
        }
    
    def get_entity_reference(self, entity_type: str, identifier: str) -> Optional[Any]:
        """Retrieve a referenced entity."""
        if entity_type in self.referenced_entities:
            if identifier in self.referenced_entities[entity_type]:
                return self.referenced_entities[entity_type][identifier]["data"]
        return None
    
    def share_data(self, key: str, value: Any) -> None:
        """Share data between agents temporarily."""
        # Ensure the data is JSON serializable
        try:
            # Test serialize/deserialize to catch any issues
            json.dumps(value)
            self.shared_data[key] = value
        except (TypeError, OverflowError):
            # If not serializable, convert to string representation
            self.shared_data[key] = str(value)
    
    def get_shared_data(self, key: str) -> Optional[Any]:
        """Retrieve shared data."""
        return self.shared_data.get(key)
    
    def get_recent_operation_summary(self) -> str:
        """Get a summary of recent operations."""
        if not self.operations_log:
            return "No operations performed yet."
            
        recent_ops = self.operations_log[-5:]  # Last 5 operations
        summary = []
        
        for op in recent_ops:
            status = "✓" if op["success"] else "✗"
            summary.append(f"{status} {op['agent']}: {op['operation']} - {str(op['details'])[:50]}")
            
        return "\n".join(summary)
    
    def sanitize_for_json(self, data: Any) -> Any:
        """Convert data to a JSON-serializable format."""
        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool)):
            return data
        elif isinstance(data, (list, tuple)):
            return [self.sanitize_for_json(item) for item in data]
        elif isinstance(data, dict):
            return {str(k): self.sanitize_for_json(v) for k, v in data.items()}
        elif hasattr(data, '__dict__'):
            # Handle custom objects by converting to dict
            return self.sanitize_for_json(data.__dict__)
        else:
            # Fall back to string representation
            return str(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary for serialization."""
        return {
            "conversation_history": self.conversation_history,
            "current_directory": self.current_directory,
            "visited_directories": list(self.visited_directories),
            "recent_files": self.recent_files,
            "operations_log": self.operations_log[-20:],  # Limit to recent operations
            "errors": self.errors[-10:],  # Limit to recent errors
            "referenced_entities": self.sanitize_for_json(self.referenced_entities),
        }

# Global context instance that all agents will share
global_context = AgentContext()
