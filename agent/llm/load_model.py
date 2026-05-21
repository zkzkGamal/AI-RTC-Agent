"""
This module defines the LLMFactory class, which is responsible for creating instances of language models (LLMs) based on a specified model name.
The factory uses a mapping of model names to their corresponding LLM classes, allowing for easy instantiation of different LLMs.
Additionally, if the model type is set to "ollama", the factory includes a method to preload the specified Ollama model into memory at startup,
ensuring faster response times when the model is first used.
The created LLM instance is then available for use in the agent's interactions.
"""
from llm.mapping import LLM_Mapping
import pathlib , environ , logging , requests

logger = logging.getLogger(__name__)
base_path = pathlib.Path(__file__).parent.parent
e = environ.Env()
e.read_env(str(base_path / ".env"))

MODEL_TYPE = e("MODEL_TYPE", default="ollama")

class LLMFactory:
    @staticmethod
    def create_llm(model_name, **kwargs):
        """Create an instance of the LLM corresponding to the given model name."""
        llm_class = LLM_Mapping.get_llm_class(model_name)
        if llm_class is None:
            raise ValueError(f"Unsupported model name: {model_name}")
        if MODEL_TYPE == "ollama":
            base_url = e("OLLAMA_BASE_URL", default="http://localhost:11434")
            LLMFactory.preload_ollama_model(model_name, base_url)
        return llm_class(model=model_name, **kwargs)
    
    def preload_ollama_model(model_name: str, base_url: str):
        logger.info(f"Preloading Ollama model: {model_name} in memory at startup...")
        try:
            url = f"{base_url.rstrip('/')}/api/generate"
            payload = {
                "model": model_name,
                "keep_alive": -1
            }
            # Preload request can take some time if the model is large
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                logger.info(f"Successfully preloaded Ollama model: {model_name}")
            else:
                logger.warning(f"Failed to preload Ollama model: {model_name}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error preloading Ollama model {model_name}: {e}")

llm = LLMFactory.create_llm(e("LLM_MODEL", default="gpt-3.5-turbo"))