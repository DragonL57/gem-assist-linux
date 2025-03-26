"""
System prompts and templates management.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

@dataclass
class Prompts:
    """System prompts configuration."""
    reasoning_prompt: str
    execution_prompt: str
    base_system_prompt: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert prompts to dictionary format.
        
        Returns:
            Dictionary of prompts
        """
        return {
            "reasoning_prompt": self.reasoning_prompt,
            "execution_prompt": self.execution_prompt,
            "base_system_prompt": self.base_system_prompt
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Prompts':
        """Create prompts from dictionary.
        
        Args:
            data: Dictionary of prompts
            
        Returns:
            Prompts instance
        """
        return cls(
            reasoning_prompt=data["reasoning_prompt"],
            execution_prompt=data["execution_prompt"],
            base_system_prompt=data["base_system_prompt"]
        )
        
class PromptManager:
    """Manager for system prompts."""
    
    def __init__(self):
        """Initialize prompt manager."""
        self._prompts: Optional[Prompts] = None
        
    def load_prompts(self, file_path: Optional[Path] = None) -> None:
        """Load prompts from file or use defaults.
        
        Args:
            file_path: Optional path to prompts file
        """
        if file_path and file_path.exists():
            with open(file_path) as f:
                data = yaml.safe_load(f)
                self._prompts = Prompts.from_dict(data)
        else:
            self._prompts = self._get_default_prompts()
            
    def save_prompts(self, file_path: Path) -> None:
        """Save current prompts to file.
        
        Args:
            file_path: Path to save prompts to
        """
        if self._prompts:
            with open(file_path, 'w') as f:
                yaml.safe_dump(self._prompts.to_dict(), f)
                
    def _get_default_prompts(self) -> Prompts:
        """Get default system prompts.
        
        Returns:
            Prompts instance with defaults
        """
        return Prompts(
            reasoning_prompt="""
You are a reasoning engine focused on planning solutions to user queries.
Your task is to think through how to solve the user's query step by step WITHOUT executing any actions.

# ROLE AND CAPABILITIES
You have access to:
- File system tools (read_file, list_dir)
- Web access tools (web_search, get_website_content)
- Code execution capabilities (execute_python_code)
- Research tools (get_arxiv_paper, summarize_research_paper)
- YouTube transcripts (get_youtube_transcript)
- System information tools (get_system_info, run_shell_command)

# REASONING REQUIREMENTS
1. Plan information gathering steps
2. Identify appropriate tools for each step
3. Consider data validation and error handling
4. Plan synthesis of gathered information

DO NOT execute tools yet - just develop a detailed plan.
""",
            execution_prompt="""
You are an execution engine responsible for implementing a pre-defined solution plan.
Your task is to execute the reasoning plan provided to you with precision and thoroughness.

# TOOL ACCESS
You have access to:
- File operations and data extraction
- Web search and content analysis
- Code execution and data processing
- Research paper access
- YouTube transcript analysis
- System commands and information

# EXECUTION REQUIREMENTS
1. Follow the reasoning plan exactly
2. Use tools as specified in the plan
3. Gather all information before synthesis
4. Validate and error check results
5. Provide clear progress updates

Focus on accurate execution of the provided plan.
""",
            base_system_prompt="""
You are an advanced terminal-based AI assistant capable of:
- File operations and data analysis
- Web search and research
- Code execution and debugging
- System monitoring and management

Approach tasks methodically with:
1. Careful planning
2. Step-by-step execution
3. Clear communication
4. Error handling

Always provide context for your actions and explain your thought process.
"""
        )
        
    @property
    def reasoning_prompt(self) -> str:
        """Get the reasoning phase prompt."""
        if not self._prompts:
            self.load_prompts()
        return self._prompts.reasoning_prompt
        
    @property
    def execution_prompt(self) -> str:
        """Get the execution phase prompt."""
        if not self._prompts:
            self.load_prompts()
        return self._prompts.execution_prompt
        
    @property
    def base_system_prompt(self) -> str:
        """Get the base system prompt."""
        if not self._prompts:
            self.load_prompts()
        return self._prompts.base_system_prompt
        
# Global instance
_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    """Get or create PromptManager singleton.
    
    Returns:
        PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
