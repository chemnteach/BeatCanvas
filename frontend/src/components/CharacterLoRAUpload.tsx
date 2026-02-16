import React, { useState, useEffect } from 'react';
import { Upload, User, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface LoRAInfo {
  name: string;
  display_name: string;
  type: string;
  description: string;
  file: string;
  trigger: string | null;
  default_weight: number;
}

interface LoRAsResponse {
  character_loras: LoRAInfo[];
  scene_loras: LoRAInfo[];
  style_loras: LoRAInfo[];
  total: number;
}

interface CharacterLoRAUploadProps {
  selectedProtagonist: string | null;
  selectedSupporting: string[];
  selectedScenes: string[];
  selectedStyle: string | null;
  onProtagonistSelect: (lora: string | null) => void;
  onSupportingSelect: (loras: string[]) => void;
  onSceneSelect: (loras: string[]) => void;
  onStyleSelect: (lora: string | null) => void;
  apiUrl?: string;
}

const CharacterLoRAUpload: React.FC<CharacterLoRAUploadProps> = ({
  selectedProtagonist,
  selectedSupporting,
  selectedScenes,
  selectedStyle,
  onProtagonistSelect,
  onSupportingSelect,
  onSceneSelect,
  onStyleSelect,
  apiUrl = 'http://localhost:8000'
}) => {
  const [characterLoras, setCharacterLoras] = useState<LoRAInfo[]>([]);
  const [sceneLoras, setSceneLoras] = useState<LoRAInfo[]>([]);
  const [styleLoras, setStyleLoras] = useState<LoRAInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    fetchAvailableLoras();
  }, []);

  const fetchAvailableLoras = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/animation/loras`);

      if (!response.ok) {
        throw new Error('Failed to fetch LoRAs');
      }

      const data: LoRAsResponse = await response.json();
      setCharacterLoras(data.character_loras);
      setSceneLoras(data.scene_loras);
      setStyleLoras(data.style_loras);
    } catch (err) {
      console.error('Error fetching LoRAs:', err);
      // Continue with empty lists
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.safetensors')) {
      setUploadError('Please upload a .safetensors file');
      return;
    }

    const loraName = prompt('Enter a name for this LoRA:');
    if (!loraName) return;

    const trigger = prompt('Enter trigger word (e.g., "ohwx"):', 'ohwx');
    if (!trigger) return;

    const description = prompt('Enter description (optional):', '');

    try {
      setUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      const formData = new FormData();
      formData.append('lora_file', file);
      formData.append('name', loraName);
      formData.append('trigger', trigger);
      formData.append('description', description || `Custom character: ${loraName}`);

      const response = await fetch(`${apiUrl}/api/animation/upload-character-lora`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadSuccess(`Successfully uploaded: ${result.name}`);

      // Refresh the LoRA list
      await fetchAvailableLoras();

      // Auto-select the newly uploaded LoRA as protagonist
      onProtagonistSelect(loraName);

      // Clear success message after 3 seconds
      setTimeout(() => setUploadSuccess(null), 3000);
    } catch (err: any) {
      console.error('Upload error:', err);
      setUploadError(err.message || 'Failed to upload LoRA');
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const toggleSupportingLora = (loraName: string) => {
    if (selectedSupporting.includes(loraName)) {
      onSupportingSelect(selectedSupporting.filter(l => l !== loraName));
    } else {
      onSupportingSelect([...selectedSupporting, loraName]);
    }
  };

  const toggleSceneLora = (loraName: string) => {
    if (selectedScenes.includes(loraName)) {
      onSceneSelect(selectedScenes.filter(l => l !== loraName));
    } else {
      onSceneSelect([...selectedScenes, loraName]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <span className="ml-3 text-gray-600">Loading character LoRAs...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <User className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-800">Character LoRAs</h3>
        </div>

        {/* Upload Button */}
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".safetensors"
            onChange={handleFileUpload}
            className="hidden"
            disabled={uploading}
          />
          <div className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            <span className="text-sm font-medium">
              {uploading ? 'Uploading...' : 'Upload LoRA'}
            </span>
          </div>
        </label>
      </div>

      {/* Upload Status */}
      {uploadSuccess && (
        <div className="flex items-center space-x-2 bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {uploadError && (
        <div className="flex items-center space-x-2 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
          <button
            onClick={() => setUploadError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Protagonist Selection */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Main Character (Protagonist)
          <span className="text-gray-500 ml-1">(Optional)</span>
        </label>
        <select
          value={selectedProtagonist || ''}
          onChange={(e) => onProtagonistSelect(e.target.value || null)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        >
          <option value="">None - Generate without character</option>
          {characterLoras.map((lora) => (
            <option key={lora.name} value={lora.name}>
              {lora.display_name} {lora.trigger && `(${lora.trigger})`}
            </option>
          ))}
        </select>
        {selectedProtagonist && characterLoras.find(l => l.name === selectedProtagonist) && (
          <p className="text-xs text-gray-600">
            {characterLoras.find(l => l.name === selectedProtagonist)?.description}
          </p>
        )}
      </div>

      {/* Supporting Characters */}
      {characterLoras.length > 1 && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Supporting Characters
            <span className="text-gray-500 ml-1">(Optional, multi-select)</span>
          </label>
          <div className="space-y-1 max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2">
            {characterLoras
              .filter(lora => lora.name !== selectedProtagonist)
              .map((lora) => (
                <label
                  key={lora.name}
                  className="flex items-center space-x-2 px-2 py-1 hover:bg-gray-50 rounded cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedSupporting.includes(lora.name)}
                    onChange={() => toggleSupportingLora(lora.name)}
                    className="rounded text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-sm">{lora.display_name}</span>
                </label>
              ))}
          </div>
        </div>
      )}

      {/* Scene LoRAs */}
      {sceneLoras.length > 0 && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Scene/Environment LoRAs
            <span className="text-gray-500 ml-1">(Optional, multi-select)</span>
          </label>
          <div className="space-y-1 max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2">
            {sceneLoras.map((lora) => (
              <label
                key={lora.name}
                className="flex items-center space-x-2 px-2 py-1 hover:bg-gray-50 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedScenes.includes(lora.name)}
                  onChange={() => toggleSceneLora(lora.name)}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <span className="text-sm">{lora.display_name}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Style LoRA */}
      {styleLoras.length > 0 && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Style LoRA
            <span className="text-gray-500 ml-1">(Optional)</span>
          </label>
          <select
            value={selectedStyle || ''}
            onChange={(e) => onStyleSelect(e.target.value || null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          >
            <option value="">None - Use animation style only</option>
            {styleLoras.map((lora) => (
              <option key={lora.name} value={lora.name}>
                {lora.display_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Info */}
      {characterLoras.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
          <p>No character LoRAs available. Upload a trained character LoRA to use custom characters in your animations.</p>
          <p className="mt-2 text-xs">
            <strong>Tip:</strong> You can train character LoRAs using tools/train_lora.sh with reference images.
          </p>
        </div>
      )}
    </div>
  );
};

export default CharacterLoRAUpload;
