import openai
from pathlib import Path
from typing import Dict, Optional, List
import os
import uuid
import shutil
from PIL import Image
import base64
import io

class ReferenceManager:
    def __init__(self):
        self.reference_dir = Path("data/references")
        self.reference_dir.mkdir(exist_ok=True)

        self.character_references = {}
        self.background_references = {}

        # Initialize OpenAI for image analysis if available
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
        else:
            self.openai_client = None

    def upload_character_reference(self, image_file, character_name: str) -> str:
        """Upload and store character reference image"""

        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        filename = f"character_{character_name}_{file_id}.jpg"
        image_path = self.reference_dir / filename

        # Save image
        with open(image_path, "wb") as f:
            f.write(image_file)

        # Analyze character features if OpenAI available
        character_description = self._analyze_character_features(image_path)

        # Store reference info
        self.character_references[character_name] = {
            "path": str(image_path),
            "description": character_description,
            "filename": filename
        }

        return str(image_path)

    def upload_background_reference(self, image_file, background_type: str) -> str:
        """Upload background reference for specific scene types"""

        file_id = str(uuid.uuid4())[:8]
        filename = f"background_{background_type}_{file_id}.jpg"
        image_path = self.reference_dir / filename

        # Save image
        with open(image_path, "wb") as f:
            f.write(image_file)

        # Analyze background style
        background_description = self._analyze_background_style(image_path)

        # Store reference info
        self.background_references[background_type] = {
            "path": str(image_path),
            "description": background_description,
            "filename": filename
        }

        return str(image_path)

    def _analyze_character_features(self, image_path: Path) -> str:
        """Analyze character features using GPT-4 Vision"""

        if not self.openai_client:
            return "Character reference uploaded (analysis unavailable without OpenAI API key)"

        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this character reference image. Provide a detailed description focusing on: physical appearance, clothing style, distinctive features, age range, and overall aesthetic. Be specific about details that would help maintain consistency across generated images."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error analyzing character features: {e}")
            return f"Character reference uploaded (analysis failed: {str(e)})"

    def _analyze_background_style(self, image_path: Path) -> str:
        """Analyze background style and mood"""

        if not self.openai_client:
            return "Background reference uploaded (analysis unavailable without OpenAI API key)"

        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this background reference image. Describe the style, mood, lighting, color palette, composition, and any distinctive visual elements. Focus on aspects that would help recreate similar backgrounds in generated images."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error analyzing background style: {e}")
            return f"Background reference uploaded (analysis failed: {str(e)})"

    def build_reference_prompt(self, base_prompt: str, character_name: str = None, background_type: str = None) -> str:
        """Build enhanced prompt with uploaded references"""

        enhanced_prompt = base_prompt

        # Add character reference if available
        if character_name and character_name in self.character_references:
            char_desc = self.character_references[character_name]["description"]
            enhanced_prompt += f"\n\nCHARACTER CONSISTENCY REFERENCE:\n{char_desc}\nEnsure the main character matches these exact details."

        # Add background reference if available
        if background_type and background_type in self.background_references:
            bg_desc = self.background_references[background_type]["description"]
            enhanced_prompt += f"\n\nBACKGROUND STYLE REFERENCE:\n{bg_desc}\nMatch this background style and mood."

        return enhanced_prompt

    def get_character_list(self) -> List[str]:
        """Get list of uploaded character names"""
        return list(self.character_references.keys())

    def get_background_types(self) -> List[str]:
        """Get list of uploaded background types"""
        return list(self.background_references.keys())

    def remove_character_reference(self, character_name: str) -> bool:
        """Remove character reference and associated file"""

        if character_name not in self.character_references:
            return False

        # Delete file
        file_path = Path(self.character_references[character_name]["path"])
        if file_path.exists():
            file_path.unlink()

        # Remove from memory
        del self.character_references[character_name]
        return True

    def remove_background_reference(self, background_type: str) -> bool:
        """Remove background reference and associated file"""

        if background_type not in self.background_references:
            return False

        # Delete file
        file_path = Path(self.background_references[background_type]["path"])
        if file_path.exists():
            file_path.unlink()

        # Remove from memory
        del self.background_references[background_type]
        return True

    def get_reference_info(self) -> Dict:
        """Get info about all uploaded references"""

        return {
            "characters": {
                name: {
                    "filename": ref["filename"],
                    "description": ref["description"][:100] + "..." if len(ref["description"]) > 100 else ref["description"]
                }
                for name, ref in self.character_references.items()
            },
            "backgrounds": {
                bg_type: {
                    "filename": ref["filename"],
                    "description": ref["description"][:100] + "..." if len(ref["description"]) > 100 else ref["description"]
                }
                for bg_type, ref in self.background_references.items()
            }
        }

    def optimize_image(self, image_path: Path, max_size: tuple = (1024, 1024)) -> Path:
        """Optimize uploaded image for processing"""

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if too large
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Save optimized version
                optimized_path = image_path.parent / f"opt_{image_path.name}"
                img.save(optimized_path, "JPEG", quality=85, optimize=True)

                # Replace original with optimized version
                optimized_path.replace(image_path)

                return image_path

        except Exception as e:
            print(f"Error optimizing image {image_path}: {e}")
            return image_path  # Return original if optimization fails