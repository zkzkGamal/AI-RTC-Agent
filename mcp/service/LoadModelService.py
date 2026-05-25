import logging

logger = logging.getLogger(__name__)


class LoadModelService:
    """
    Shared Whisper model lifecycle manager.

    A single instance is created at module load so every service/tool uses the
    same model object after startup warmup.
    """

    def __init__(self) -> None:
        self.model = None

    def get_model(self):
        """Lazily load the Whisper model on first access."""
        if self.model is None:
            import whisper

            self.model = whisper.load_model("small")
            logger.info("Whisper model loaded.")
        return self.model

    def preload_model(self) -> None:
        """Warm the shared Whisper model during server startup."""
        self.get_model()


load_model_service = LoadModelService()
