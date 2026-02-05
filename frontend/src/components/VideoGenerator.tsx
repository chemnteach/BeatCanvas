import React, { useState, useEffect } from 'react';
import { Upload, Play, Download, Settings, Loader2 } from 'lucide-react';
import AudioUpload from './AudioUpload';
import ProgressTracker from './ProgressTracker';
import StoryboardEditor from './StoryboardEditor';
import ProviderSettings from './ProviderSettings';
import VideoPreview from './VideoPreview';
import ReferenceImageUpload from './ReferenceImageUpload';
import SceneEditModal from './SceneEditModal';

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

interface TaskProgress {
  id: string;
  status: 'started' | 'complete' | 'error';
  progress: string;
  storyboard: StoryboardScene[];
  video_url?: string;
}

type WorkflowStage = 'upload' | 'prompts' | 'analysis' | 'storyboard-review' | 'generation' | 'complete';

const VideoGenerator: React.FC = () => {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [contentPrompt, setContentPrompt] = useState('');
  const [stylePrompt, setStylePrompt] = useState('');
  const [suggestedStyles, setSuggestedStyles] = useState<string[]>([]);
  const [selectedStyle, setSelectedStyle] = useState('');
  const [qualityTier, setQualityTier] = useState('professional');
  const [providerPreference, setProviderPreference] = useState<'auto' | 'dalle' | 'novelai' | 'both'>('auto');

  // Workflow state management
  const [currentStage, setCurrentStage] = useState<WorkflowStage>('upload');
  const [isStoryboardApproved, setIsStoryboardApproved] = useState(false);
  const [generationStartTime, setGenerationStartTime] = useState<number | null>(null);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null);

  // Reference image uploads
  const [characterImages, setCharacterImages] = useState<File[]>([]);
  const [backgroundImages, setBackgroundImages] = useState<File[]>([]);
  const [characterDescriptions, setCharacterDescriptions] = useState<string[]>([]);
  const [backgroundDescriptions, setBackgroundDescriptions] = useState<string[]>([]);

  const [currentTask, setCurrentTask] = useState<TaskProgress | null>(null);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  const [showSettings, setShowSettings] = useState(false);
  const [storyboard, setStoryboard] = useState<StoryboardScene[]>([]);
  const [videoUrl, setVideoUrl] = useState<string>('');

  // Scene editing state
  const [editingSceneIndex, setEditingSceneIndex] = useState<number | undefined>(undefined);
  const [isRegenerating, setIsRegenerating] = useState(false);

  useEffect(() => {
    // Cleanup websocket on unmount
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [websocket]);

  // Style suggestion functionality
  const getStyleSuggestions = async (description: string) => {
    if (!description.trim()) return;

    try {
      const response = await fetch('http://localhost:8002/api/style-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description })
      });

      if (response.ok) {
        const suggestions = await response.json();
        setSuggestedStyles(suggestions.styles);
      }
    } catch (error) {
      console.error('Error getting style suggestions:', error);
      // Fallback to common styles
      setSuggestedStyles([
        'Photorealistic HD',
        'Cinematic film style',
        'Anime/manga style',
        'Digital art illustration',
        'Abstract geometric',
        'Oil painting style'
      ]);
    }
  };

  // Debounced style suggestion
  useEffect(() => {
    const timer = setTimeout(() => {
      if (contentPrompt.trim()) {
        getStyleSuggestions(contentPrompt);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [contentPrompt]);

  // Reference image management
  const handleCharacterImageAdd = (files: FileList | null) => {
    if (files) {
      const newImages = Array.from(files);
      setCharacterImages(prev => [...prev, ...newImages]);
      setCharacterDescriptions(prev => [...prev, ...new Array(newImages.length).fill('')]);
    }
  };

  const handleBackgroundImageAdd = (files: FileList | null) => {
    if (files) {
      const newImages = Array.from(files);
      setBackgroundImages(prev => [...prev, ...newImages]);
      setBackgroundDescriptions(prev => [...prev, ...new Array(newImages.length).fill('')]);
    }
  };

  const removeCharacterImage = (index: number) => {
    setCharacterImages(prev => prev.filter((_, i) => i !== index));
    setCharacterDescriptions(prev => prev.filter((_, i) => i !== index));
  };

  const removeBackgroundImage = (index: number) => {
    setBackgroundImages(prev => prev.filter((_, i) => i !== index));
    setBackgroundDescriptions(prev => prev.filter((_, i) => i !== index));
  };

  const updateCharacterDescription = (index: number, description: string) => {
    setCharacterDescriptions(prev => {
      const newDescriptions = [...prev];
      newDescriptions[index] = description;
      return newDescriptions;
    });
  };

  const updateBackgroundDescription = (index: number, description: string) => {
    setBackgroundDescriptions(prev => {
      const newDescriptions = [...prev];
      newDescriptions[index] = description;
      return newDescriptions;
    });
  };

  // Step 1: Analyze audio and generate storyboard
  const handleAnalyzeAndStoryboard = async () => {
    if (!audioFile || !contentPrompt.trim() || !selectedStyle.trim()) {
      alert('Please upload an audio file, provide content prompt, and select a style');
      return;
    }

    setCurrentStage('analysis');
    setGenerationStartTime(Date.now());

    try {
      const formData = new FormData();
      formData.append('audio', audioFile);
      formData.append('content_prompt', contentPrompt);
      formData.append('style_prompt', selectedStyle);
      formData.append('quality_tier', qualityTier);

      // Add character reference images
      characterImages.forEach((image, index) => {
        formData.append(`character_image_${index}`, image);
        formData.append(`character_description_${index}`, characterDescriptions[index] || '');
      });

      // Add background reference images
      backgroundImages.forEach((image, index) => {
        formData.append(`background_image_${index}`, image);
        formData.append(`background_description_${index}`, backgroundDescriptions[index] || '');
      });

      const response = await fetch('http://localhost:8002/api/analyze-and-storyboard', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to analyze audio and create storyboard');
      }

      const result = await response.json();

      setCurrentTask({
        id: result.task_id,
        status: 'started',
        progress: 'Audio analysis complete, storyboard ready for review',
        storyboard: result.storyboard
      });

      setStoryboard(result.storyboard);
      setCurrentStage('storyboard-review');

    } catch (error) {
      console.error('Error in analysis phase:', error);
      alert('Failed to analyze audio. Please try again.');
      setCurrentStage('prompts');
    }
  };

  // Step 2: Generate images and video (after storyboard approval)
  const handleGenerateVideo = async () => {
    if (!isStoryboardApproved || !currentTask) {
      alert('Please approve the storyboard first');
      return;
    }

    setCurrentStage('generation');
    setGenerationStartTime(Date.now());

    try {
      const formData = new FormData();
      formData.append('task_id', currentTask.id);
      formData.append('approved_storyboard', JSON.stringify(storyboard));

      const response = await fetch('http://localhost:8002/api/generate-images-and-video', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to start video generation');
      }

      const result = await response.json();
      const taskId = result.task_id;

      // Initialize task state
      setCurrentTask({
        id: taskId,
        status: 'started',
        progress: 'Starting video generation...',
        storyboard: []
      });

      // Connect to WebSocket for progress updates
      const ws = new WebSocket(`ws://localhost:8002/ws/${taskId}`);
      setWebsocket(ws);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setCurrentTask(data);

        // Update progress and stage based on status
        if (data.status === 'complete' && data.video_url) {
          setCurrentStage('complete');
          setVideoUrl(data.video_url);
        }

        // Update storyboard if provided
        if (data.storyboard) {
          setStoryboard(data.storyboard);
        }

        // Calculate time remaining based on progress
        if (generationStartTime && data.progress) {
          const elapsed = Date.now() - generationStartTime;
          // Rough estimate based on typical generation times
          const estimatedTotal = storyboard.length * 30000; // 30 seconds per scene
          const remaining = Math.max(0, estimatedTotal - elapsed);
          setEstimatedTimeRemaining(remaining);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setCurrentTask(prev => prev ? {
          ...prev,
          status: 'error',
          progress: 'Connection error'
        } : null);
      };

    } catch (error) {
      console.error('Error starting generation:', error);
      alert('Failed to start video generation. Please try again.');
    }
  };

  const handleStoryboardUpdate = (updatedStoryboard: StoryboardScene[]) => {
    setStoryboard(updatedStoryboard);
  };

  // Scene editing functions
  const handleSceneEdit = (sceneIndex: number) => {
    setEditingSceneIndex(sceneIndex);
  };

  const handleSceneEditClose = () => {
    setEditingSceneIndex(undefined);
  };

  const handleSceneRegeneate = async (sceneIndex: number, newDescription: string, provider: string, effects: string[]) => {
    if (!currentTask) return;

    setIsRegenerating(true);

    try {
      const response = await fetch('http://localhost:8002/api/regenerate-scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: currentTask.id,
          scene_index: sceneIndex,
          new_description: newDescription,
          provider: provider,
          effects: effects
        })
      });

      if (!response.ok) {
        throw new Error('Failed to regenerate scene');
      }

      const result = await response.json();

      // Update the storyboard with the new scene
      setStoryboard(prev => {
        const updated = [...prev];
        if (result.updated_scene) {
          updated[sceneIndex] = result.updated_scene;
        }
        return updated;
      });

      // Close edit modal
      setEditingSceneIndex(undefined);

      // Optional: Trigger video rebuild
      if (window.confirm(`Scene ${sceneIndex + 1} regenerated successfully! Would you like to rebuild the video with this change?`)) {
        await handleVideoRebuild();
      }

    } catch (error) {
      console.error('Error regenerating scene:', error);
      alert('Failed to regenerate scene. Please try again.');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleVideoRebuild = async () => {
    if (!currentTask) return;

    try {
      const response = await fetch(`http://localhost:8002/api/rebuild-video?task_id=${currentTask.id}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to start video rebuild');
      }

      // Connect to WebSocket to monitor rebuild progress
      if (websocket) {
        websocket.close();
      }

      const ws = new WebSocket(`ws://localhost:8002/ws/${currentTask.id}`);
      setWebsocket(ws);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setCurrentTask(data);

        // Update video URL when rebuild is complete
        if (data.status === 'complete' && data.video_url) {
          setVideoUrl(data.video_url);
        }
      };

    } catch (error) {
      console.error('Error rebuilding video:', error);
      alert('Failed to rebuild video. Please try again.');
    }
  };

  const isGenerating = currentTask && currentTask.status === 'started';
  const isComplete = currentTask && currentTask.status === 'complete';
  const hasError = currentTask && currentTask.status === 'error';

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl md:text-6xl font-bold text-white">
          Transform Music into
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-purple-400"> Visual Stories</span>
        </h1>
        <p className="text-xl text-dark-300 max-w-2xl mx-auto">
          Upload your song, describe your vision, and watch AI create a professional music video with editable storyboards
        </p>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Panel - Enhanced Workflow */}
        <div className="space-y-6">
          {/* Workflow Progress Indicator */}
          <div className="bg-dark-700 rounded-xl p-4 border border-dark-600">
            <div className="flex items-center justify-between text-sm">
              {(['upload', 'prompts', 'analysis', 'storyboard-review', 'generation', 'complete'] as const).map((stage, index) => (
                <div key={stage} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                    currentStage === stage ? 'bg-primary-500 text-white' :
                    (['upload', 'prompts', 'analysis'].indexOf(currentStage) > ['upload', 'prompts', 'analysis'].indexOf(stage)) ||
                    (currentStage === 'storyboard-review' && index < 3) ||
                    (currentStage === 'generation' && index < 4) ||
                    (currentStage === 'complete' && index < 5) ? 'bg-green-600 text-white' :
                    'bg-dark-600 text-dark-400'
                  }`}>
                    {index + 1}
                  </div>
                  {index < 5 && <div className="w-4 h-0.5 bg-dark-600 mx-1"></div>}
                </div>
              ))}
            </div>
            <div className="mt-2 text-xs text-dark-400 text-center">
              {currentStage === 'upload' && 'Upload audio file'}
              {currentStage === 'prompts' && 'Describe content and style'}
              {currentStage === 'analysis' && 'Analyzing audio...'}
              {currentStage === 'storyboard-review' && 'Review and approve storyboard'}
              {currentStage === 'generation' && 'Generating images and video...'}
              {currentStage === 'complete' && 'Video ready!'}
            </div>
          </div>

          {/* Step 1: Audio Upload */}
          {currentStage === 'upload' && (
            <>
              <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                  <Upload className="h-5 w-5 mr-2" />
                  Upload Your Song
                </h2>
                <AudioUpload
                  onFileSelect={setAudioFile}
                  selectedFile={audioFile}
                />

                {audioFile && (
                  <button
                    onClick={() => setCurrentStage('prompts')}
                    className="mt-4 w-full bg-primary-500 hover:bg-primary-600 text-white font-medium py-3 px-6 rounded-lg transition-colors"
                  >
                    Continue to Content & Style
                  </button>
                )}
              </div>
            </>
          )}

          {/* Step 2: Content & Style Prompts */}
          {currentStage === 'prompts' && (
            <>
              {/* Content Prompt */}
              <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
                <h2 className="text-xl font-semibold text-white mb-4">
                  1. Describe Your Content
                </h2>
                <textarea
                  value={contentPrompt}
                  onChange={(e) => setContentPrompt(e.target.value)}
                  placeholder="What should happen in your video? Example: 'A dancer moving underwater through coral reefs, graceful movements synchronized with the music'"
                  className="w-full h-24 p-3 bg-dark-800 border border-dark-500 rounded-lg text-white placeholder-dark-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                />
                <div className="mt-2 text-sm text-dark-400">
                  Describe the scenes, actions, and visual narrative
                </div>
              </div>

              {/* Style Selection */}
              <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
                <h2 className="text-xl font-semibold text-white mb-4">
                  2. Choose Visual Style
                </h2>

                {/* Style Input */}
                <input
                  type="text"
                  value={stylePrompt}
                  onChange={(e) => setStylePrompt(e.target.value)}
                  placeholder="Describe the visual style (e.g., 'photorealistic HD', 'anime style', 'oil painting')"
                  className="w-full p-3 bg-dark-800 border border-dark-500 rounded-lg text-white placeholder-dark-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />

                {/* AI Style Suggestions */}
                {suggestedStyles.length > 0 && (
                  <div className="mt-4">
                    <p className="text-dark-300 text-sm mb-2">AI Suggestions:</p>
                    <div className="grid grid-cols-2 gap-2">
                      {suggestedStyles.map((style, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedStyle(style)}
                          className={`p-2 text-sm rounded-lg border transition-colors ${
                            selectedStyle === style
                              ? 'bg-primary-500 border-primary-500 text-white'
                              : 'bg-dark-800 border-dark-600 text-dark-300 hover:border-primary-500'
                          }`}
                        >
                          {style}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Custom Style */}
                {stylePrompt && !suggestedStyles.includes(stylePrompt) && (
                  <button
                    onClick={() => setSelectedStyle(stylePrompt)}
                    className="mt-2 w-full p-2 text-sm bg-dark-800 border border-dark-600 text-dark-300 rounded-lg hover:border-primary-500 transition-colors"
                  >
                    Use Custom Style: "{stylePrompt}"
                  </button>
                )}
              </div>

              {/* Reference Images */}
              <ReferenceImageUpload
                type="character"
                images={characterImages}
                descriptions={characterDescriptions}
                onImageAdd={handleCharacterImageAdd}
                onImageRemove={removeCharacterImage}
                onDescriptionUpdate={updateCharacterDescription}
              />

              <ReferenceImageUpload
                type="background"
                images={backgroundImages}
                descriptions={backgroundDescriptions}
                onImageAdd={handleBackgroundImageAdd}
                onImageRemove={removeBackgroundImage}
                onDescriptionUpdate={updateBackgroundDescription}
              />

              {/* Settings */}
              <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">
                    Generation Settings
                  </h2>
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className="p-2 text-dark-400 hover:text-white transition-colors"
                  >
                    <Settings className="h-5 w-5" />
                  </button>
                </div>

                {showSettings && (
                  <ProviderSettings
                    qualityTier={qualityTier}
                    onQualityChange={setQualityTier}
                    providerPreference={providerPreference}
                    onProviderChange={setProviderPreference}
                  />
                )}

                <button
                  onClick={handleAnalyzeAndStoryboard}
                  disabled={!audioFile || !contentPrompt.trim() || !selectedStyle.trim()}
                  className="w-full bg-gradient-to-r from-primary-500 to-purple-500 hover:from-primary-600 hover:to-purple-600 disabled:from-dark-600 disabled:to-dark-600 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center disabled:cursor-not-allowed"
                >
                  <Play className="h-5 w-5 mr-2" />
                  Create Storyboard
                </button>
              </div>
            </>
          )}

          {/* Step 3: Analysis Progress */}
          {currentStage === 'analysis' && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <h2 className="text-xl font-semibold text-white mb-4">
                Analyzing Your Music
              </h2>
              <div className="flex items-center space-x-3">
                <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />
                <span className="text-dark-300">Creating your personalized storyboard...</span>
              </div>
              {estimatedTimeRemaining && (
                <div className="mt-2 text-sm text-dark-400">
                  Estimated time: {Math.round(estimatedTimeRemaining / 1000)}s remaining
                </div>
              )}
            </div>
          )}

          {/* Step 4: Storyboard Review */}
          {currentStage === 'storyboard-review' && storyboard.length > 0 && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <h2 className="text-xl font-semibold text-white mb-4">
                Review Your Storyboard
              </h2>
              <p className="text-dark-300 mb-4">
                Review and edit your scenes before generating images. This will cost approximately ${(storyboard.length * 0.08).toFixed(2)} for {storyboard.length} scenes.
              </p>

              <div className="space-y-2 mb-6">
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="approve-storyboard"
                    checked={isStoryboardApproved}
                    onChange={(e) => setIsStoryboardApproved(e.target.checked)}
                    className="w-4 h-4 text-primary-500 bg-dark-800 border-dark-600 rounded focus:ring-primary-500"
                  />
                  <label htmlFor="approve-storyboard" className="text-white">
                    I approve this storyboard and want to generate the video
                  </label>
                </div>
                <p className="text-sm text-dark-400 ml-7">
                  You can still edit individual scenes in the storyboard editor on the right
                </p>
              </div>

              <button
                onClick={handleGenerateVideo}
                disabled={!isStoryboardApproved}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 disabled:from-dark-600 disabled:to-dark-600 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center disabled:cursor-not-allowed"
              >
                <Play className="h-5 w-5 mr-2" />
                Generate Video
              </button>
            </div>
          )}

          {/* Step 5: Generation Progress */}
          {currentStage === 'generation' && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <h2 className="text-xl font-semibold text-white mb-4">
                Generating Your Video
              </h2>
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />
                  <span className="text-dark-300">
                    {currentTask?.progress || 'Generating images...'}
                  </span>
                </div>
                {estimatedTimeRemaining && (
                  <div className="text-sm text-dark-400">
                    Estimated time: {Math.round(estimatedTimeRemaining / 1000)}s remaining
                  </div>
                )}
                {generationStartTime && (
                  <div className="text-sm text-dark-400">
                    Elapsed: {Math.round((Date.now() - generationStartTime) / 1000)}s
                  </div>
                )}
              </div>

              <button
                onClick={() => {
                  if (websocket) websocket.close();
                  setCurrentStage('prompts');
                  setCurrentTask(null);
                }}
                className="mt-4 w-full bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel Generation
              </button>
            </div>
          )}

          {/* Step 6: Complete */}
          {currentStage === 'complete' && videoUrl && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <h2 className="text-xl font-semibold text-white mb-4">
                🎉 Video Complete!
              </h2>
              <p className="text-dark-300 mb-4">
                Your music video has been generated successfully!
              </p>
              <button
                onClick={() => {
                  setCurrentStage('upload');
                  setAudioFile(null);
                  setContentPrompt('');
                  setStylePrompt('');
                  setSelectedStyle('');
                  setStoryboard([]);
                  setVideoUrl('');
                  setCurrentTask(null);
                  setIsStoryboardApproved(false);
                }}
                className="w-full bg-primary-500 hover:bg-primary-600 text-white font-medium py-3 px-6 rounded-lg transition-colors"
              >
                Create Another Video
              </button>
            </div>
          )}

          {/* Error Display */}
          {hasError && (
            <div className="bg-red-900/20 border border-red-700 rounded-xl p-4">
              <p className="text-red-400">
                {currentTask?.progress}
              </p>
            </div>
          )}
        </div>

        {/* Right Panel - Progress & Results */}
        <div className="space-y-6">
          {/* Enhanced Progress Tracker */}
          {(currentTask || currentStage !== 'upload') && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <h3 className="text-lg font-medium text-white mb-4">
                {currentStage === 'analysis' && '🎵 Analyzing Music'}
                {currentStage === 'storyboard-review' && '📝 Storyboard Ready'}
                {currentStage === 'generation' && '🎨 Creating Video'}
                {currentStage === 'complete' && '✅ Complete'}
                {currentTask && <span className="ml-2 text-sm text-dark-400">#{currentTask.id.slice(-6)}</span>}
              </h3>

              {currentTask && (
                <ProgressTracker
                  progress={currentTask.progress}
                  status={currentTask.status}
                />
              )}

              {/* Real-time stats */}
              {generationStartTime && (
                <div className="mt-4 text-sm text-dark-400 space-y-1">
                  <div>Elapsed: {Math.round((Date.now() - generationStartTime) / 1000)}s</div>
                  {estimatedTimeRemaining && currentStage === 'generation' && (
                    <div>Remaining: ~{Math.round(estimatedTimeRemaining / 1000)}s</div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Storyboard Editor with enhanced controls */}
          {storyboard.length > 0 && (
            <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">
                  Storyboard ({storyboard.length} scenes)
                </h3>
                {currentStage === 'storyboard-review' && (
                  <div className="text-sm text-dark-400">
                    Cost: ~${(storyboard.length * 0.08).toFixed(2)}
                  </div>
                )}
              </div>

              <StoryboardEditor
                storyboard={storyboard}
                onStoryboardUpdate={handleStoryboardUpdate}
                isEditable={currentStage === 'storyboard-review'}
              />

              {currentStage === 'storyboard-review' && (
                <div className="mt-4 p-3 bg-blue-900/20 border border-blue-700 rounded-lg">
                  <p className="text-blue-400 text-sm">
                    💡 You can edit scene descriptions, timing, and effects before generating images.
                    Changes made here will be reflected in the final video.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Video Preview */}
          {currentStage === 'complete' && videoUrl && (
            <VideoPreview
              videoUrl={videoUrl}
              storyboard={storyboard}
              onDownload={() => window.open(videoUrl, '_blank')}
              onSceneEdit={handleSceneEdit}
              editingSceneIndex={editingSceneIndex}
            />
          )}

          {/* Scene Edit Modal */}
          <SceneEditModal
            isOpen={editingSceneIndex !== undefined}
            scene={editingSceneIndex !== undefined ? storyboard[editingSceneIndex] : null}
            sceneIndex={editingSceneIndex || 0}
            onClose={handleSceneEditClose}
            onSave={handleSceneRegeneate}
            isRegenerating={isRegenerating}
            currentImageUrl={
              editingSceneIndex !== undefined && storyboard[editingSceneIndex]?.images?.length
                ? storyboard[editingSceneIndex].images![0]
                : undefined
            }
          />

          {/* Dynamic Cost Estimate */}
          <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
            <h3 className="text-lg font-medium text-white mb-2">
              Cost Information
            </h3>
            <div className="space-y-2 text-sm">
              {storyboard.length > 0 ? (
                <div className="space-y-1">
                  <div className="flex justify-between text-white">
                    <span>Your Video ({storyboard.length} scenes)</span>
                    <span className="font-medium">${(storyboard.length * 0.08).toFixed(2)}</span>
                  </div>
                  <div className="text-xs text-dark-400">
                    Includes: Concept generation + {storyboard.length} AI images + Video assembly
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex justify-between text-dark-300">
                    <span>Basic (12 scenes)</span>
                    <span>~$1.00</span>
                  </div>
                  <div className="flex justify-between text-dark-300">
                    <span>Professional (24 scenes)</span>
                    <span>~$2.00</span>
                  </div>
                  <div className="flex justify-between text-dark-300">
                    <span>Cinematic (48 scenes)</span>
                    <span>~$4.00</span>
                  </div>
                </div>
              )}

              {characterImages.length > 0 && (
                <div className="text-xs text-green-400">
                  + Character references: Included for consistency
                </div>
              )}

              {backgroundImages.length > 0 && (
                <div className="text-xs text-green-400">
                  + Background references: Included for style guidance
                </div>
              )}

              <div className="text-xs text-dark-400 mt-3 pt-2 border-t border-dark-600">
                💳 Pay-per-use pricing. Only charged for successful generations.
              </div>
            </div>
          </div>

          {/* Quick Tips */}
          {currentStage === 'prompts' && (
            <div className="bg-purple-900/20 border border-purple-700 rounded-xl p-4">
              <h4 className="text-purple-400 font-medium mb-2">💡 Pro Tips</h4>
              <ul className="text-sm text-dark-300 space-y-1">
                <li>• Be specific about visual style for better results</li>
                <li>• Upload character references for consistency</li>
                <li>• Background images help establish mood/setting</li>
                <li>• Review storyboard before generation to save costs</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoGenerator;