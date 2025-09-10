from huggingface_hub import InferenceClient
from ..config import settings

class AIService:
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize AI client via Hugging Face API"""

        if settings.hf_token:
            try:
                self.client = InferenceClient(
                    model="m42-health/Llama3-Med42-8B",
                    token=settings.hf_token,
                    headers={"Accept-Encoding": "identity"}
                )
                return True
            
            except Exception as e:
                print(f"Failed to initialize AI client: {e}")
                return False
        
    
    def get_client(self) -> InferenceClient:
        """Get the AI client with error handling"""
        if self.client is None:
            raise RuntimeError("AI service not initialized")
        return self.client
    
    def is_available(self) -> bool:
        """Check if AI client is available"""
        return self.client is not None
    
    def get_model_info(self) -> dict:
        """Get information about the current model"""
        return {
            "model_name": "m42-health/Llama3-Med42-8B",
            "is_available": self.is_available(),
            "use_api": settings.use_api,
            "initialized": self.client is not None
        }
