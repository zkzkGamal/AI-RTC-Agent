"""
This module provides the LoadPrompts class, which is responsible for loading and formatting prompts for the agent. 
It uses the langchain_core library to load prompts from YAML files and format them with relevant context such as the user's home directory 
and project root. The formatted prompts are then returned as messages that can be used by the agent in its interactions.
LoadPrompts now supports two modes:
- load_prompt()         → fully formatted messages (for static prompts like router/conv)
- load_partial_prompt() → partially formatted template (for act prompts with runtime vars)
"""
from langchain_core.prompts import load_prompt
import os, pathlib, logging

logger = logging.getLogger(__name__)
base_path = pathlib.Path(__file__).parent.parent


class LoadPrompts:
    def __init__(self):
        self.base_path = base_path
        self._static = {
            "home"        : os.path.expanduser("~"),
            "project_root": str(self.base_path),
            "name"        : "",
        }

    def _resolve(self, prompt_path: str):
        path = self.base_path / "prompts" / prompt_path
        return load_prompt(path)

    def load_prompt(self, prompt_path: str):
        """
        Fully format a prompt with static vars only.
        Use for: router, conv — prompts that have no runtime variables.
        Returns: list[BaseMessage]
        """
        prompt = self._resolve(prompt_path)
        return prompt.format_prompt(**self._static).to_messages()

    def load_partial_prompt(self, prompt_path: str):
        """
        Partially format a prompt — fills static vars now, leaves runtime
        vars (route, tool_result, user_message, etc.) for invocation time.
        Use for: act — prompts that need state variables injected at runtime.
        Returns: BasePromptTemplate (still has unfilled variables)
        """
        prompt = self._resolve(prompt_path)
        return prompt.partial(**{
            k: v for k, v in self._static.items()
            if k in prompt.input_variables
        })