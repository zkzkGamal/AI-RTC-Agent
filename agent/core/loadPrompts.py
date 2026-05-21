"""
This module provides the LoadPrompts class, which is responsible for loading and formatting prompts for the agent. 
It uses the langchain_core library to load prompts from YAML files and format them with relevant context such as the user's home directory 
and project root. The formatted prompts are then returned as messages that can be used by the agent in its interactions.
"""
from langchain_core.prompts import load_prompt
import os , pathlib , logging

logger = logging.getLogger(__name__)
base_path = pathlib.Path(__file__).parent.parent

class LoadPrompts:
    def __init__(self):
        self.base_path = base_path
    
    def load_prompt(self, prompt_path):
        prompt_path = self.base_path / "prompts" / prompt_path
        prompt = load_prompt(prompt_path)
        home = os.path.expanduser("~")
        project_root = self.base_path
        name = ""
        return prompt.format_prompt(home=home, project_root=project_root, name=name).to_messages()