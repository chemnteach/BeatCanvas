import React, { useState } from 'react';
import { Edit3, RefreshCw, Play, Pause, Image as ImageIcon, Clock } from 'lucide-react';

interface StoryboardScene {
  timestamp_start: number;
  timestamp_end: number;
  description: string;
  visual_style: string;
  mood: string;
  camera_direction: string;
  image_prompt: string;
  effects: string[];
  images?: string[];
  selected_image?: number;
}

interface StoryboardEditorProps {
  storyboard: StoryboardScene[];
  onStoryboardUpdate: (updated: StoryboardScene[]) => void;
  isEditable: boolean;
}

const StoryboardEditor: React.FC<StoryboardEditorProps> = ({
  storyboard,
  onStoryboardUpdate,
  isEditable
}) => {
  const [selectedScene, setSelectedScene] = useState<number>(0);
  const [editingScene, setEditingScene] = useState<number | null>(null);
  const [editPrompt, setEditPrompt] = useState('');

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleEditScene = (sceneIndex: number) => {
    setEditingScene(sceneIndex);
    setEditPrompt(storyboard[sceneIndex].description);
  };

  const handleSaveEdit = async () => {
    if (editingScene === null) return;

    // TODO: Implement API call to regenerate scene
    console.log(`Regenerating scene ${editingScene} with prompt: ${editPrompt}`);

    setEditingScene(null);
    setEditPrompt('');
  };

  const handleCancelEdit = () => {
    setEditingScene(null);
    setEditPrompt('');
  };

  const handleImageSelect = (sceneIndex: number, imageIndex: number) => {
    const updatedStoryboard = [...storyboard];
    updatedStoryboard[sceneIndex] = {
      ...updatedStoryboard[sceneIndex],
      selected_image: imageIndex
    };
    onStoryboardUpdate(updatedStoryboard);
  };

  return (
    <div className="bg-dark-700 rounded-xl border border-dark-600 overflow-hidden">
      <div className="p-6 border-b border-dark-600">
        <h2 className="text-xl font-semibold text-white flex items-center">
          <ImageIcon className="h-5 w-5 mr-2" />
          Storyboard
          <span className="ml-2 text-sm text-dark-400">
            ({storyboard.length} scenes)
          </span>
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        {/* Scene List */}
        <div className="lg:border-r border-dark-600 bg-dark-800">
          <div className="p-4 border-b border-dark-600">
            <h3 className="text-sm font-medium text-white">Scenes</h3>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {storyboard.map((scene, index) => (
              <button
                key={index}
                onClick={() => setSelectedScene(index)}
                className={`w-full p-3 text-left border-b border-dark-700 transition-colors ${
                  selectedScene === index
                    ? 'bg-primary-900/30 border-primary-500'
                    : 'hover:bg-dark-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">
                    Scene {index + 1}
                  </span>
                  <div className="flex items-center text-xs text-dark-400">
                    <Clock className="h-3 w-3 mr-1" />
                    {formatTime(scene.timestamp_start)}
                  </div>
                </div>
                <div className="text-xs text-dark-400 mb-1">
                  {scene.mood} • {scene.camera_direction}
                </div>
                <div className="text-xs text-dark-300 line-clamp-2">
                  {scene.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Scene Details */}
        <div className="lg:col-span-2 p-6">
          {storyboard[selectedScene] && (
            <div className="space-y-4">
              {/* Scene Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-white">
                    Scene {selectedScene + 1}
                  </h3>
                  <p className="text-sm text-dark-400">
                    {formatTime(storyboard[selectedScene].timestamp_start)} -{' '}
                    {formatTime(storyboard[selectedScene].timestamp_end)} ({' '}
                    {(storyboard[selectedScene].timestamp_end - storyboard[selectedScene].timestamp_start).toFixed(1)}s)
                  </p>
                </div>

                {isEditable && (
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleEditScene(selectedScene)}
                      className="p-2 text-dark-400 hover:text-white border border-dark-500 rounded-lg hover:border-dark-400 transition-colors"
                    >
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button className="p-2 text-dark-400 hover:text-white border border-dark-500 rounded-lg hover:border-dark-400 transition-colors">
                      <RefreshCw className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              {/* Editing Mode */}
              {editingScene === selectedScene ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">
                      Edit Scene Description
                    </label>
                    <textarea
                      value={editPrompt}
                      onChange={(e) => setEditPrompt(e.target.value)}
                      className="w-full h-24 p-3 bg-dark-800 border border-dark-500 rounded-lg text-white placeholder-dark-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                      placeholder="Describe how you want this scene to look..."
                    />
                  </div>
                  <div className="flex space-x-3">
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                    >
                      Regenerate Scene
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 border border-dark-500 text-dark-300 hover:text-white hover:border-dark-400 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                /* Scene Display */
                <div className="space-y-4">
                  {/* Scene Description */}
                  <div>
                    <h4 className="text-sm font-medium text-white mb-2">Description</h4>
                    <p className="text-dark-200 text-sm leading-relaxed">
                      {storyboard[selectedScene].description}
                    </p>
                  </div>

                  {/* Scene Details */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-medium text-white mb-1">Mood</h4>
                      <p className="text-dark-300 text-sm">{storyboard[selectedScene].mood}</p>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-white mb-1">Camera</h4>
                      <p className="text-dark-300 text-sm">{storyboard[selectedScene].camera_direction}</p>
                    </div>
                  </div>

                  {/* Effects */}
                  {storyboard[selectedScene].effects.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-white mb-2">Effects</h4>
                      <div className="flex flex-wrap gap-1">
                        {storyboard[selectedScene].effects.map((effect, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-dark-600 text-dark-200 text-xs rounded"
                          >
                            {effect}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Generated Images */}
                  {storyboard[selectedScene].images && storyboard[selectedScene].images!.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-white mb-2">Generated Images</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {storyboard[selectedScene].images!.map((imageUrl, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleImageSelect(selectedScene, idx)}
                            className={`relative aspect-video rounded-lg overflow-hidden border-2 transition-all ${
                              storyboard[selectedScene].selected_image === idx
                                ? 'border-primary-500 shadow-lg shadow-primary-500/20'
                                : 'border-dark-600 hover:border-dark-400'
                            }`}
                          >
                            <img
                              src={imageUrl}
                              alt={`Scene ${selectedScene + 1} variation ${idx + 1}`}
                              className="w-full h-full object-cover"
                            />
                            {storyboard[selectedScene].selected_image === idx && (
                              <div className="absolute top-2 right-2 bg-primary-500 text-white text-xs px-1.5 py-0.5 rounded">
                                Selected
                              </div>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoryboardEditor;