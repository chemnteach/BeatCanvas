import json
import os
import yaml
import re
from dataclasses import dataclass
from typing import Dict, List
from llama_cpp import Llama

def load_config(filename):
    path = os.path.expanduser(f"~/AI_Workspace/synterra/beatcanvas/backend/config/{filename}")
    if not os.path.exists(path): return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class SceneAnalyzerSkill:
    def __init__(self):
        self.model_path = os.path.expanduser("~/AI_Workspace/synterra/models/Phi-3-mini-4k-instruct.gguf")
        self.llm = None

    def _build_dynamic_system_prompt(self):
        # 1. Load all configs
        loras = load_config("loras.yaml")
        checkpoints = load_config("checkpoints.yaml")
        training = load_config("brain_training.yaml")

        # 2. Format Registries
        lora_docs = "\n".join([f'- "{k}": {v.get("description")}' for k, v in loras.items() if v.get("enabled")])
        ckpt_docs = "\n".join([f'- "{k}": {v.get("description")}' for k, v in checkpoints.items() if v.get("enabled")])

        # 3. Format Examples
        example_blocks = []
        for ex in training.get("examples", []):
            example_blocks.append(f"Input: \"{ex['input']}\"\nOutput:\n{json.dumps(ex['output'], indent=4)}")
        
        examples_str = "\n\n".join(example_blocks)

        # 4. Assemble the final Instruction
        return f"""You are a technical JSON-only API. Categorize requests into JSON.
        
### AVAILABLE ENGINES:
{ckpt_docs}

### AVAILABLE FILTERS:
{lora_docs}

### EXAMPLES:
{examples_str}

### YOUR TURN:
Respond ONLY with valid JSON."""

    def _load_model(self):
        if self.llm: return
        self.llm = Llama(model_path=self.model_path, n_ctx=2048, n_gpu_layers=33, verbose=False)

    def analyze_scene(self, scene_description, energy_level="medium"):
        self._load_model()
        system_instruction = self._build_dynamic_system_prompt()
        
        user_message = f"SCENE: {scene_description}\nENERGY: {energy_level}"
        prompt_text = f"<|user|>\n{system_instruction}\n\n{user_message}\n<|end|>\n<|assistant|>"

        output = self.llm(prompt_text, max_tokens=512, stop=["<|end|>"], temperature=0.1)
        raw_response = output["choices"][0]["text"].strip()
        
        return self._parse_response(raw_response, scene_description)

    def _parse_response(self, raw_response, original_prompt):
        try:
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            data = json.loads(json_match.group(0)) if json_match else json.loads(raw_response)
            
            return SceneAnalysis(
                loras=data.get("loras", {"cinema": 0.8}),
                enhanced_prompt=data.get("enhanced_prompt", original_prompt),
                checkpoint=data.get("checkpoint", "photoreal"),
                reasoning=data.get("reasoning", "Success")
            )
        except Exception:
            return SceneAnalysis({"cinema":0.8}, original_prompt, "photoreal", "Fallback")

    def unload(self):
        if self.llm:
            del self.llm
            self.llm = None

@dataclass
class SceneAnalysis:
    loras: Dict[str, float]
    enhanced_prompt: str
    checkpoint: str
    reasoning: str
    @property
    def lora_string(self) -> str:
        return ",".join(self.loras.keys())
