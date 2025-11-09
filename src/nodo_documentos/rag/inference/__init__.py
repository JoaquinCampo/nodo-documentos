"""Cerebras Inference integration for LLM chat completions."""

from nodo_documentos.rag.inference.service import (
    CerebrasInferenceService,
    get_inference_service,
)

__all__ = ["CerebrasInferenceService", "get_inference_service"]
