"""Family Knowledge-Base subsystem.

Provides typed models, a shared loader, and a clear error type for
family-specific KB files:

  config/families/{family}_review_hints.json      — LLM guidance layer
  config/families/{family}_behavioral_patterns.json — deterministic enforcement layer

Usage::

    from src.services.kb import KnowledgeBaseLoader, KBLoadError, ReviewHint, BehavioralPattern

    hints = KnowledgeBaseLoader.load_review_hints("words")
    patterns = KnowledgeBaseLoader.load_behavioral_patterns("words")
"""

from .loader import KBLoadError, KnowledgeBaseLoader
from .models import BehavioralPattern, ReviewHint

__all__ = [
    "KBLoadError",
    "KnowledgeBaseLoader",
    "ReviewHint",
    "BehavioralPattern",
]
