import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, Loader2, Zap } from 'lucide-react';

interface StoryboardScene {
  timestamp_start: number;
  timestamp_end: number;
  description: string;
  mood: string;
  effects: string[];
  visual_style?: string;
  camera_direction?: string;
  image_prompt?: string;
}

interface SceneEditModalProps {
  isOpen: boolean;
  scene: StoryboardScene | null;
  sceneIndex: number;
  onClose: () => void;
  onSave: (sceneIndex: number, newDescription: string, provider: string, effects: string[]) => void;
  isRegenerating?: boolean;
  currentImageUrl?: string;
}

const AVAILABLE_EFFECTS = [
  { id: 'zoom_in', label: 'Zoom In', description: 'Slowly zoom into the scene' },
  { id: 'zoom_out', label: 'Zoom Out', description: 'Slowly zoom out from the scene' },
  { id: 'pan_left', label: 'Pan Left', description: 'Camera moves left across scene' },
  { id: 'pan_right', label: 'Pan Right', description: 'Camera moves right across scene' },
  { id: 'fade_in', label: 'Fade In', description: 'Gradual fade in effect' },
  { id: 'fade_out', label: 'Fade Out', description: 'Gradual fade out effect' }
];

const AI_PROVIDERS = [
  {
    id: 'auto',
    name: 'Auto (Nano Banana First)',
    description: 'Smart selection with Nano Banana preference',
    cost: 0.04
  },
  {
    id: 'nano_banana',
    name: 'Nano Banana',
    description: 'Google Gemini - Best for character consistency',
    cost: 0.04
  },
  {
    id: 'dalle',
    name: 'DALL-E 3',
    description: 'OpenAI - Best for photorealistic scenes',
    cost: 0.08
  },
  {
    id: 'novelai',
    name: 'NovelAI',
    description: 'Best for anime/artistic styles',
    cost: 0.06
  }
];

const SceneEditModal: React.FC<SceneEditModalProps> = ({
  isOpen,
  scene,
  sceneIndex,
  onClose,
  onSave,
  isRegenerating = false,
  currentImageUrl
}) => {
  const [description, setDescription] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('auto');
  const [selectedEffects, setSelectedEffects] = useState<string[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Initialize form data when scene changes
  useEffect(() => {
    if (scene) {
      setDescription(scene.description || scene.image_prompt || '');
      setSelectedEffects(scene.effects || []);
      setHasUnsavedChanges(false);
    }
  }, [scene]);

  // Track changes
  useEffect(() => {
    if (scene) {
      const originalDescription = scene.description || scene.image_prompt || '';
      const originalEffects = scene.effects || [];

      const hasChanges =
        description !== originalDescription ||
        JSON.stringify(selectedEffects) !== JSON.stringify(originalEffects);

      setHasUnsavedChanges(hasChanges);
    }
  }, [description, selectedEffects, scene]);

  // Handle effect toggle
  const toggleEffect = (effectId: string) => {
    setSelectedEffects(prev =>
      prev.includes(effectId)
        ? prev.filter(id => id !== effectId)
        : [...prev, effectId]
    );
  };

  // Handle save
  const handleSave = () => {
    if (scene && description.trim()) {
      onSave(sceneIndex, description.trim(), selectedProvider, selectedEffects);
    }
  };

  // Handle close with confirmation if unsaved changes
  const handleClose = () => {
    if (hasUnsavedChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  // Format time helper
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Get selected provider info
  const selectedProviderInfo = AI_PROVIDERS.find(p => p.id === selectedProvider) || AI_PROVIDERS[0];

  if (!isOpen || !scene) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">
              Edit Scene {sceneIndex + 1}
            </h2>
            <p className="text-gray-400 text-sm">
              {formatTime(scene.timestamp_start)} - {formatTime(scene.timestamp_end)}
              {' '}({formatTime(scene.timestamp_end - scene.timestamp_start)} duration)
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {/* Current Scene Info */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-start space-x-4">
              {/* Current Image Preview */}
              {currentImageUrl && (
                <div className="flex-shrink-0">
                  <img
                    src={currentImageUrl}
                    alt={`Scene ${sceneIndex + 1}`}
                    className="w-24 h-16 object-cover rounded border border-gray-600"
                  />
                </div>
              )}

              {/* Scene Details */}
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-400 mb-1">Current Scene:</div>
                <div className="text-white text-sm mb-2">{scene.description}</div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="bg-blue-600 text-white px-2 py-1 rounded">
                    {scene.mood}
                  </span>
                  {scene.effects?.map(effect => (
                    <span key={effect} className="bg-gray-600 text-white px-2 py-1 rounded">
                      {effect}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Description Input */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Scene Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full h-24 p-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Describe what you want to see in this scene..."
              disabled={isRegenerating}
            />
            <p className="text-xs text-gray-400 mt-1">
              Example: "Two characters sharing a romantic kiss under moonlight"
            </p>
          </div>

          {/* Effects Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Visual Effects
            </label>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_EFFECTS.map(effect => (
                <button
                  key={effect.id}
                  onClick={() => toggleEffect(effect.id)}
                  disabled={isRegenerating}
                  className={`p-3 rounded-lg border text-sm text-left transition-colors ${
                    selectedEffects.includes(effect.id)
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'bg-gray-800 border-gray-600 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <div className="font-medium">{effect.label}</div>
                  <div className="text-xs text-gray-400">{effect.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* AI Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              AI Provider
            </label>
            <div className="space-y-2">
              {AI_PROVIDERS.map(provider => (
                <label
                  key={provider.id}
                  className={`flex items-start p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProvider === provider.id
                      ? 'bg-blue-600 border-blue-500'
                      : 'bg-gray-800 border-gray-600 hover:bg-gray-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={provider.id}
                    checked={selectedProvider === provider.id}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    disabled={isRegenerating}
                    className="mt-1 sr-only"
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-medium">{provider.name}</span>
                      <span className="text-sm text-gray-300">${provider.cost.toFixed(2)}</span>
                    </div>
                    <p className="text-sm text-gray-300 mt-1">{provider.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Cost Estimate */}
          <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-yellow-400" />
              <span className="text-yellow-400 font-medium">Cost Estimate</span>
            </div>
            <p className="text-yellow-300 text-sm mt-1">
              Regenerating this scene will cost approximately ${selectedProviderInfo.cost.toFixed(2)} using {selectedProviderInfo.name}.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-400">
            {hasUnsavedChanges && (
              <span className="text-yellow-400">• Unsaved changes</span>
            )}
          </div>

          <div className="flex space-x-3">
            <button
              onClick={handleClose}
              disabled={isRegenerating}
              className="px-4 py-2 text-gray-300 hover:text-white border border-gray-600 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!description.trim() || !hasUnsavedChanges || isRegenerating}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRegenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Regenerating...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  <span>Regenerate Scene - ${selectedProviderInfo.cost.toFixed(2)}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SceneEditModal;