"""
Custom exceptions for BeatCanvas image generation.

These exceptions provide structured error information that can be:
1. Categorized by type (rate limit, auth, validation, etc.)
2. Marked as retryable or not
3. Surfaced to the frontend UI

This replaces the "silent failure antipattern" where errors were logged
to console but returned as empty lists, making debugging impossible.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for categorization and frontend display"""
    RATE_LIMIT = "RATE_LIMIT"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    AUTH_ERROR = "AUTH_ERROR"
    INVALID_PROMPT = "INVALID_PROMPT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    NO_CANDIDATES = "NO_CANDIDATES"
    NO_CONTENT = "NO_CONTENT"
    NO_IMAGE_DATA = "NO_IMAGE_DATA"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class ImageGenerationError(Exception):
    """
    Base exception for image generation failures.

    Provides structured error information including:
    - error_code: Categorized error type for programmatic handling
    - provider: Which AI provider failed (nano_banana, dalle, novelai)
    - scene_timestamp: Which scene in the storyboard failed
    - retryable: Whether the operation should be retried

    Usage:
        raise ImageGenerationError(
            "Rate limit exceeded",
            provider="nano_banana",
            scene_timestamp=45.5,
            error_code=ErrorCode.RATE_LIMIT,
            retryable=True
        )
    """

    def __init__(
        self,
        message: str,
        provider: str = "",
        scene_timestamp: float = 0.0,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        retryable: bool = False,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.provider = provider
        self.scene_timestamp = scene_timestamp
        self.error_code = error_code
        self.retryable = retryable
        self.original_exception = original_exception
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "message": self.message,
            "provider": self.provider,
            "scene_timestamp": self.scene_timestamp,
            "error_code": self.error_code.value,
            "retryable": self.retryable
        }


class RateLimitError(ImageGenerationError):
    """
    Raised when API rate limit is hit.

    Always retryable - the operation should succeed after waiting.
    Includes retry_after hint for how long to wait.
    """

    def __init__(
        self,
        provider: str,
        scene_timestamp: float,
        retry_after: int = 45,
        message: Optional[str] = None
    ):
        self.retry_after = retry_after
        super().__init__(
            message or f"{provider} rate limit exceeded - wait {retry_after}s",
            provider=provider,
            scene_timestamp=scene_timestamp,
            error_code=ErrorCode.RATE_LIMIT,
            retryable=True
        )


class ModelNotFoundError(ImageGenerationError):
    """
    Raised when the specified model is not found (404).

    Not retryable - requires code change to use different model.
    This typically happens when Google deprecates a model.
    """

    def __init__(
        self,
        provider: str,
        model_name: str,
        scene_timestamp: float = 0.0
    ):
        self.model_name = model_name
        super().__init__(
            f"Model '{model_name}' not found - may be deprecated",
            provider=provider,
            scene_timestamp=scene_timestamp,
            error_code=ErrorCode.MODEL_NOT_FOUND,
            retryable=False
        )


class AuthenticationError(ImageGenerationError):
    """
    Raised when API key is missing, invalid, or lacks permission.

    Not retryable without configuration change.
    """

    def __init__(
        self,
        provider: str,
        message: Optional[str] = None
    ):
        super().__init__(
            message or f"Authentication failed for {provider} - check API key",
            provider=provider,
            scene_timestamp=0.0,
            error_code=ErrorCode.AUTH_ERROR,
            retryable=False
        )


class ResponseValidationError(ImageGenerationError):
    """
    Raised when API response is malformed or missing expected data.

    May be retryable - sometimes APIs return partial responses under load.
    """

    def __init__(
        self,
        provider: str,
        scene_timestamp: float,
        missing_field: str,
        retryable: bool = True
    ):
        self.missing_field = missing_field
        super().__init__(
            f"API response missing {missing_field}",
            provider=provider,
            scene_timestamp=scene_timestamp,
            error_code=ErrorCode.NO_CONTENT,
            retryable=retryable
        )


class PromptRejectedError(ImageGenerationError):
    """
    Raised when the prompt is rejected by the API (content policy, etc.)

    Not retryable with same prompt - requires prompt modification.
    """

    def __init__(
        self,
        provider: str,
        scene_timestamp: float,
        reason: Optional[str] = None
    ):
        super().__init__(
            f"Prompt rejected by {provider}" + (f": {reason}" if reason else ""),
            provider=provider,
            scene_timestamp=scene_timestamp,
            error_code=ErrorCode.INVALID_PROMPT,
            retryable=False
        )


@dataclass
class GenerationResult:
    """
    Structured result from a single scene generation attempt.

    This replaces the ambiguous "return empty list on failure" pattern.
    Now callers can distinguish between:
    - success=True, images=[...] -> Generation worked
    - success=True, images=[] -> Generation worked but produced no images (unlikely)
    - success=False, error="..." -> Generation failed, here's why

    Usage:
        result = await generate_nano_banana_images(...)
        if result.success:
            process(result.images)
        else:
            log_error(result.error, result.error_code)
            if result.retryable:
                retry_later()
    """
    success: bool
    images: List  # List[GeneratedImage] - avoiding circular import
    error: Optional[str] = None
    error_code: Optional[str] = None
    retryable: bool = False
    provider: str = ""
    scene_timestamp: float = 0.0

    @staticmethod
    def ok(images: List, provider: str = "", scene_timestamp: float = 0.0) -> 'GenerationResult':
        """Create a successful result"""
        return GenerationResult(
            success=True,
            images=images,
            provider=provider,
            scene_timestamp=scene_timestamp
        )

    @staticmethod
    def fail(
        error: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        retryable: bool = False,
        provider: str = "",
        scene_timestamp: float = 0.0
    ) -> 'GenerationResult':
        """Create a failed result"""
        return GenerationResult(
            success=False,
            images=[],
            error=error,
            error_code=error_code.value,
            retryable=retryable,
            provider=provider,
            scene_timestamp=scene_timestamp
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "image_count": len(self.images),
            "error": self.error,
            "error_code": self.error_code,
            "retryable": self.retryable,
            "provider": self.provider,
            "scene_timestamp": self.scene_timestamp
        }
