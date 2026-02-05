"""
Prompt translation using Phi-3 mini model.
Converts natural language prompts to Danbooru-style tags for anime image generation.
"""
from typing import Optional

try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")

from utils.model_loader import get_model_path


class PhiTranslator:
    """Translates natural language to Danbooru tags using Phi-3."""

    SYSTEM_PROMPT = """You are an expert at converting natural language descriptions into Danbooru-style tags.
Danbooru tags are comma-separated descriptors used for anime/manga image generation.

Rules:
1. Output ONLY comma-separated tags, no explanations
2. Use underscores for multi-word tags (e.g., "long_hair", "red_eyes")
3. Include quality tags (e.g., "masterpiece", "high_quality", "detailed")
4. Include artist style if mentioned
5. Order: quality tags, then subject, then attributes, then background
6. Keep tags concise and specific

Example:
Input: "A girl with long purple hair wearing a school uniform in a cherry blossom garden"
Output: masterpiece, high_quality, 1girl, long_hair, purple_hair, school_uniform, cherry_blossoms, garden, outdoors
"""

    def __init__(self, model_name: str = "Phi-3-mini-4k-instruct.gguf"):
        """
        Initialize the Phi-3 translator.

        Args:
            model_name: Filename of the Phi-3 GGUF model
        """
        self.model_path = get_model_path("llm", model_name)
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the Phi-3 GGUF model into memory."""
        print(f"Loading Phi-3 model from: {self.model_path}")

        # Initialize llama.cpp with Phi-3
        self.model = Llama(
            model_path=str(self.model_path),
            n_ctx=4096,  # Phi-3 supports 4k context
            n_gpu_layers=-1,  # Offload to GPU if available
            n_batch=512,
            verbose=False,
            chat_format="chatml"  # Phi-3 uses ChatML format
        )

        print("Phi-3 model loaded successfully")

    def translate_to_danbooru(
        self,
        natural_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 200
    ) -> str:
        """
        Translate a natural language prompt to Danbooru tags.

        Args:
            natural_prompt: Natural language description
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            str: Comma-separated Danbooru tags
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        # Create chat messages
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": natural_prompt}
        ]

        # Generate response
        response = self.model.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=["User:", "\n\n"]
        )

        # Extract tags from response
        tags = response['choices'][0]['message']['content'].strip()

        # Clean up the output
        tags = self._clean_tags(tags)

        return tags

    def _clean_tags(self, tags: str) -> str:
        """
        Clean and validate the generated tags.

        Args:
            tags: Raw tag string from model

        Returns:
            str: Cleaned comma-separated tags
        """
        # Remove any explanatory text (just in case)
        if '\n' in tags:
            tags = tags.split('\n')[0]

        # Remove quotes if present
        tags = tags.replace('"', '').replace("'", '')

        # Normalize spacing
        tag_list = [tag.strip() for tag in tags.split(',')]
        tag_list = [tag for tag in tag_list if tag]  # Remove empty tags

        # Join back
        cleaned = ', '.join(tag_list)

        return cleaned

    def translate_with_style(
        self,
        natural_prompt: str,
        style: str,
        quality_preset: str = "high"
    ) -> str:
        """
        Translate with additional style and quality modifiers.

        Args:
            natural_prompt: Natural language description
            style: Art style (e.g., "anime", "manga", "realistic")
            quality_preset: Quality level ("low", "medium", "high", "ultra")

        Returns:
            str: Danbooru tags with style modifiers
        """
        quality_tags = {
            "low": "",
            "medium": "high_quality, ",
            "high": "masterpiece, high_quality, detailed, ",
            "ultra": "masterpiece, best_quality, ultra_detailed, perfect_lighting, "
        }

        # Get base tags
        base_tags = self.translate_to_danbooru(natural_prompt)

        # Prepend quality and style
        quality = quality_tags.get(quality_preset, quality_tags["high"])
        styled_tags = f"{quality}{style}, {base_tags}"

        return styled_tags

    def batch_translate(self, prompts: list) -> list:
        """
        Translate multiple prompts in batch.

        Args:
            prompts: List of natural language prompts

        Returns:
            list: List of Danbooru tag strings
        """
        return [self.translate_to_danbooru(prompt) for prompt in prompts]

    def __del__(self):
        """Cleanup model on deletion."""
        if self.model is not None:
            del self.model


if __name__ == "__main__":
    # Test prompt translation
    translator = PhiTranslator()

    test_prompts = [
        "A girl with long purple hair wearing a school uniform in a cherry blossom garden",
        "A cyberpunk city at night with neon lights",
        "A cute cat wearing a wizard hat casting a spell"
    ]

    print("Testing prompt translation:\n")
    for prompt in test_prompts:
        print(f"Input: {prompt}")
        tags = translator.translate_to_danbooru(prompt)
        print(f"Tags: {tags}\n")

    # Test with style
    print("Testing with style:")
    styled = translator.translate_with_style(
        "a magical forest",
        style="anime",
        quality_preset="ultra"
    )
    print(f"Styled tags: {styled}")
