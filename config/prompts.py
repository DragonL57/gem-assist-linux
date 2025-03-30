"""
System prompts and templates management.
"""
import asyncio # Added for lock
from dataclasses import dataclass, field # Import field
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

@dataclass
class Prompts:
    """System prompts configuration."""
    reasoning_prompt: str
    execution_prompt: str
    base_system_prompt: str
    self_reflection_prompt: str # Added new field
    final_response_refinement_prompt: str # <<< ADDED

    def to_dict(self) -> Dict[str, str]:
        """Convert prompts to dictionary format.

        Returns:
            Dictionary of prompts
        """
        return {
            "reasoning_prompt": self.reasoning_prompt,
            "execution_prompt": self.execution_prompt,
            "base_system_prompt": self.base_system_prompt,
            "self_reflection_prompt": self.self_reflection_prompt, # Added to dict
            "final_response_refinement_prompt": self.final_response_refinement_prompt # <<< ADDED
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Prompts':
        """Create prompts from dictionary.

        Args:
            data: Dictionary of prompts

        Returns:
            Prompts instance
        """
        # Use .get() with default values for backward compatibility or missing keys
        return cls(
            reasoning_prompt=data.get("reasoning_prompt", ""), # Provide default empty string
            execution_prompt=data.get("execution_prompt", ""), # Provide default empty string
            base_system_prompt=data.get("base_system_prompt", ""), # Provide default empty string
            self_reflection_prompt=data.get("self_reflection_prompt", ""), # Added with default
            final_response_refinement_prompt=data.get("final_response_refinement_prompt", "") # <<< ADDED with default
        )

class PromptManager:
    """Manager for system prompts."""

    def __init__(self):
        """Initialize prompt manager."""
        self._prompts: Optional[Prompts] = None
        self._load_lock = asyncio.Lock() # Add lock for async safety

    async def load_prompts(self, file_path: Optional[Path] = None) -> None: # Made async
        """Load prompts from file or use defaults asynchronously."""
        async with self._load_lock:
             # Only load if not already loaded
             if self._prompts is None:
                  default_prompts_file = Path(__file__).parent / "prompts.yml"
                  load_path = file_path if file_path and file_path.exists() else default_prompts_file

                  if load_path.exists():
                      try:
                          with open(load_path) as f:
                              data = yaml.safe_load(f)
                              if data: # Ensure file wasn't empty
                                  self._prompts = Prompts.from_dict(data)
                              else:
                                  print(f"Warning: Prompt file {load_path} is empty. Using defaults.")
                                  self._prompts = self._get_default_prompts()
                      except (yaml.YAMLError, IOError, KeyError, TypeError) as e: # Added TypeError
                          # Log error and fall back to defaults
                          print(f"Warning: Failed to load prompts from {load_path}: {e}. Using defaults.")
                          self._prompts = self._get_default_prompts()
                  else:
                      print(f"Warning: Prompt file {load_path} not found. Using defaults.")
                      self._prompts = self._get_default_prompts()

    async def ensure_prompts_loaded(self, file_path: Optional[Path] = None) -> None:
        """Ensure prompts are loaded, calling load_prompts if necessary."""
        if self._prompts is None:
             await self.load_prompts(file_path)
        if self._prompts is None: # Still None after attempting load?
            raise RuntimeError("Failed to load prompts even after calling load_prompts.")

    def save_prompts(self, file_path: Path) -> None:
        """Save current prompts to file.

        Args:
            file_path: Path to save prompts to
        """
        if self._prompts:
            try:
                with open(file_path, 'w') as f:
                    # Ensure proper YAML formatting
                    yaml.safe_dump(self._prompts.to_dict(), f, default_flow_style=None, sort_keys=False, allow_unicode=True)
            except IOError as e:
                print(f"Error saving prompts to {file_path}: {e}")

    def _get_default_prompts(self) -> Prompts:
        """Get default system prompts.

        Returns:
            Prompts instance with defaults
        """
        # NOTE: These defaults might be outdated compared to the YAML file.
        # They are primarily a fallback if the YAML load fails.
        return Prompts(
            reasoning_prompt="Default Reasoning Prompt: Plan steps and tools.",
            execution_prompt="Default Execution Prompt: Execute the plan.",
            base_system_prompt="Default Base Prompt: You are a helpful assistant.",
            self_reflection_prompt="Default Reflection Prompt: Reflect on the process.", # Added default
            final_response_refinement_prompt="Default Refinement Prompt: Refine the response." # <<< ADDED default
        )

    # Properties now ensure prompts are loaded before access
    # NOTE: In an async context, direct property access might lead to attempting
    # to load prompts synchronously if ensure_prompts_loaded wasn't awaited first.
    # Consider making properties async or ensuring loading happens explicitly at startup.
    # For now, keeping them sync but adding RuntimeError if not loaded.
    @property
    def reasoning_prompt(self) -> str:
        """Get the reasoning phase prompt."""
        if self._prompts is None:
            # This might happen if ensure_prompts_loaded wasn't awaited correctly before access
            raise RuntimeError("Prompts not loaded. Call ensure_prompts_loaded first.")
        return self._prompts.reasoning_prompt

    @property
    def execution_prompt(self) -> str:
        """Get the execution phase prompt."""
        if self._prompts is None:
            raise RuntimeError("Prompts not loaded. Call ensure_prompts_loaded first.")
        return self._prompts.execution_prompt

    @property
    def base_system_prompt(self) -> str:
        """Get the base system prompt."""
        if self._prompts is None:
            raise RuntimeError("Prompts not loaded. Call ensure_prompts_loaded first.")
        return self._prompts.base_system_prompt

    @property
    def self_reflection_prompt(self) -> str: # Added property
        """Get the self-reflection prompt."""
        if self._prompts is None:
            raise RuntimeError("Prompts not loaded. Call ensure_prompts_loaded first.")
        return self._prompts.self_reflection_prompt

    @property
    def final_response_refinement_prompt(self) -> str: # <<< ADDED Property
        """Get the final response refinement prompt."""
        if self._prompts is None:
            raise RuntimeError("Prompts not loaded. Call ensure_prompts_loaded first.")
        return self._prompts.final_response_refinement_prompt

# Global instance (Kept for potential direct use, though config access is preferred)
_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    """Get or create PromptManager singleton.

    Returns:
        PromptManager instance
    """
    # This singleton pattern might need adjustment in an async context
    # Depending on how it's used. Loading should ideally happen once at startup.
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
        # Consider loading prompts here if file path is known globally,
        # but usually done via Config object.
    return _prompt_manager
