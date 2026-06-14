"""
This module defines the LLM_Mapping class, which provides a simple mapping of model names to their corresponding LLM classes.
The mapping includes popular models such as "gpt-3.5-turbo", "gpt-4", "gemini-2.5-flash", and custom Ollama models like "qwen-3.5:4b" and "qwen-3.5:0.8b".
The get_llm_class method allows for easy retrieval of the LLM class based on the model name, facilitating the creation of LLM instances in the agent's interactions.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama


class LLM_Mapping:
    """A simple mapping of model names to their corresponding LLM classes."""
    mapping = {
        "gpt-3.5-turbo": ChatOpenAI,
        "gpt-4": ChatOpenAI,
        "gemini-2.5-flash": ChatGoogleGenerativeAI,
        "qwen-3.5:4b": ChatOllama,
        "qwen-3.5:0.8b": ChatOllama,
        "qwen3.5:4b": ChatOllama,
        "qwen3.5:0.8b": ChatOllama,
        "qwen3.5:2b-q4_K_M": ChatOllama,
        "qwen3.5:4b-q4_K_M": ChatOllama,
        "qwen3.5:6b-q4_K_M": ChatOllama,
        "qwen3.5:8b-q4_K_M": ChatOllama,
    }

    @classmethod
    def get_llm_class(cls, model_name):
        """Return the LLM class corresponding to the given model name."""
        return cls.mapping.get(model_name)