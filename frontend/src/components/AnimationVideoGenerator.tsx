import React, { useState, useEffect } from 'react';
import { Upload, Play, Download, Loader2, Film, AlertCircle, CheckCircle } from 'lucide-react';
import AudioUpload from './AudioUpload';
import AnimationStyleSelector from './AnimationStyleSelector';
import CharacterLoRAUpload from './CharacterLoRAUpload';

interface AnimationTaskProgress {
  task_id: string;
  status: 'started' | 'animating' | 'complete' | 'error';
  progress: string;
  video_url?: string;
  output_path?: string;
}

type WorkflowStage = 'upload' | 'configure' | 'generating' | 'complete';

const AnimationVideoGenerator: React.FC = () => {
  // Audio state
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [uploadedAudioPath, setUploadedAudioPath] = useState<string>('');

  // Animation configuration
  const [animationStyle, setAnimationStyle] = useState<string>('watercolor');
  const [qualityTier, setQualityTier] = useState<string>('professional');

  // Character LoRA state
  const [protagonistLora, setProtagonistLora] = useState<string | null>(null);
  const [supportingLoras, setSupportingLoras] = useState<string[]>([]);
  const [sceneLoras, setSceneLoras] = useState<string[]>([]);
  const [styleLora, setStyleLora] = useState<string | null>(null);

  // Workflow state
  const [currentStage, setCurrentStage] = useState<WorkflowStage>('upload');
  const [currentTask, setCurrentTask] = useState<AnimationTaskProgress | null>(null);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fps, setFps] = useState(24);
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);

  const apiUrl = 'http://localhost:8000';

  useEffect(() => {
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [websocket]);

  const handleAudioUpload = async (file: File | null) => {
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('audio', file);

      const response = await fetch(`${apiUrl}/api/upload-audio`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload audio');
      }

      const data = await response.json();
      setAudioFile(file);
      setUploadedAudioPath(data.path || `data/uploads/${file.name}`);
      setCurrentStage('configure');
    } catch (err: any) {
      console.error('Audio upload error:', err);
      alert(`Failed to upload audio: ${err.message}`);
    }
  };

  const startAnimationGeneration = async () => {
    if (!audioFile || !uploadedAudioPath) {
      alert('Please upload an audio file first');
      return;
    }

    if (!animationStyle) {
      alert('Please select an animation style');
      return;
    }

    try {
      setIsGenerating(true);
      setGenerationError(null);
      setCurrentStage('generating');

      const taskId = `animation_${Date.now()}`;

      // Create animation request
      const request = {
        task_id: taskId,
        audio_path: uploadedAudioPath,
        animation_style: animationStyle,
        protagonist_lora: protagonistLora,
        supporting_loras: supportingLoras.length > 0 ? supportingLoras : null,
        scene_loras: sceneLoras.length > 0 ? sceneLoras : null,
        style_lora: styleLora,
        quality_tier: qualityTier,
        use_stock_footage: false,
        fps: fps,
        width: width,
        height: height
      };

      const response = await fetch(`${apiUrl}/api/animation/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start animation generation');
      }

      const data = await response.json();

      setCurrentTask({
        task_id: taskId,
        status: data.status,
        progress: data.message
      });

      // Connect WebSocket for progress updates
      const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);

      ws.onopen = () => {
        console.log('WebSocket connected for animation task:', taskId);
      };

      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          console.log('Animation progress update:', update);

          setCurrentTask(update);

          if (update.status === 'complete' && update.video_url) {
            setVideoUrl(update.video_url);
            setCurrentStage('complete');
            setIsGenerating(false);
          } else if (update.status === 'error') {
            setGenerationError(update.progress || 'Animation generation failed');
            setIsGenerating(false);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setGenerationError('Connection error during animation generation');
        setIsGenerating(false);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

      setWebsocket(ws);

    } catch (err: any) {
      console.error('Animation generation error:', err);
      setGenerationError(err.message || 'Failed to start animation generation');
      setIsGenerating(false);
    }
  };

  const resetWorkflow = () => {
    setAudioFile(null);
    setUploadedAudioPath('');
    setCurrentStage('upload');
    setCurrentTask(null);
    setIsGenerating(false);
    setGenerationError(null);
    setVideoUrl('');

    if (websocket) {
      websocket.close();
      setWebsocket(null);
    }
  };

  const downloadVideo = () => {
    if (videoUrl) {
      window.open(`${apiUrl}${videoUrl}`, '_blank');
    }
  };

  const getProgressMessage = (): string => {
    if (!currentTask) return 'Waiting to start...';
    return currentTask.progress;
  };

  const getProgressPercentage = (): number => {
    if (!currentTask) return 0;

    const status = currentTask.status;
    if (status === 'started') return 10;
    if (status === 'animating') return 50;
    if (status === 'complete') return 100;
    return 0;
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center space-x-3">
          <Film className="w-10 h-10 text-purple-600" />
          <h1 className="text-4xl font-bold text-gray-900">Animation Video Generator</h1>
        </div>
        <p className="text-gray-600">
          Transform your music into stunning animated videos with 16 unique art styles
        </p>
      </div>

      {/* Stage Indicator */}
      <div className="flex items-center justify-center space-x-2 text-sm">
        {['upload', 'configure', 'generating', 'complete'].map((stage, idx) => (
          <React.Fragment key={stage}>
            <div
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                currentStage === stage
                  ? 'bg-purple-600 text-white'
                  : idx < ['upload', 'configure', 'generating', 'complete'].indexOf(currentStage)
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              {stage === 'upload' && '1. Upload Audio'}
              {stage === 'configure' && '2. Configure Style'}
              {stage === 'generating' && '3. Generating'}
              {stage === 'complete' && '4. Complete'}
            </div>
            {idx < 3 && <div className="w-8 h-0.5 bg-gray-300" />}
          </React.Fragment>
        ))}
      </div>

      {/* Content based on stage */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-8">
        {/* Stage 1: Upload Audio */}
        {currentStage === 'upload' && (
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Upload Your Music</h2>
            <AudioUpload
              onFileSelect={handleAudioUpload}
              selectedFile={audioFile}
            />
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
              <strong>Tip:</strong> Upload any music file (MP3, WAV, etc.). The animation will be perfectly synced to your audio!
            </div>
          </div>
        )}

        {/* Stage 2: Configure Animation */}
        {currentStage === 'configure' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-gray-800">Configure Animation</h2>
              <button
                onClick={resetWorkflow}
                className="text-sm text-purple-600 hover:text-purple-700 font-medium"
              >
                Change Audio
              </button>
            </div>

            {/* Audio Info */}
            {audioFile && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-700">
                  <strong>Audio:</strong> {audioFile.name}
                </p>
              </div>
            )}

            {/* Animation Style Selector */}
            <AnimationStyleSelector
              selectedStyle={animationStyle}
              onStyleSelect={setAnimationStyle}
              apiUrl={apiUrl}
            />

            {/* Quality Tier */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Quality Tier
              </label>
              <select
                value={qualityTier}
                onChange={(e) => setQualityTier(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="basic">Basic (12 scenes, ~15 min)</option>
                <option value="professional">Professional (24 scenes, ~30 min) - Recommended</option>
                <option value="cinematic">Cinematic (48 scenes, ~60 min)</option>
              </select>
            </div>

            {/* Character LoRAs */}
            <CharacterLoRAUpload
              selectedProtagonist={protagonistLora}
              selectedSupporting={supportingLoras}
              selectedScenes={sceneLoras}
              selectedStyle={styleLora}
              onProtagonistSelect={setProtagonistLora}
              onSupportingSelect={setSupportingLoras}
              onSceneSelect={setSceneLoras}
              onStyleSelect={setStyleLora}
              apiUrl={apiUrl}
            />

            {/* Advanced Options */}
            <div>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-sm text-purple-600 hover:text-purple-700 font-medium"
              >
                {showAdvanced ? '▼' : '▶'} Advanced Options
              </button>

              {showAdvanced && (
                <div className="mt-3 space-y-3 bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        FPS
                      </label>
                      <input
                        type="number"
                        value={fps}
                        onChange={(e) => setFps(Number(e.target.value))}
                        min={12}
                        max={60}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Width
                      </label>
                      <input
                        type="number"
                        value={width}
                        onChange={(e) => setWidth(Number(e.target.value))}
                        step={64}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Height
                      </label>
                      <input
                        type="number"
                        value={height}
                        onChange={(e) => setHeight(Number(e.target.value))}
                        step={64}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Generate Button */}
            <button
              onClick={startAnimationGeneration}
              disabled={!animationStyle || isGenerating}
              className="w-full py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-semibold text-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-3"
            >
              <Play className="w-6 h-6" />
              <span>Generate Animated Video</span>
            </button>
          </div>
        )}

        {/* Stage 3: Generating */}
        {currentStage === 'generating' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-semibold text-gray-800 text-center">
              Creating Your Animation...
            </h2>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500 ease-out"
                  style={{ width: `${getProgressPercentage()}%` }}
                />
              </div>
              <p className="text-center text-sm text-gray-600">
                {getProgressPercentage()}% Complete
              </p>
            </div>

            {/* Status Message */}
            <div className="flex items-center justify-center space-x-3 py-8">
              <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
              <p className="text-lg text-gray-700">{getProgressMessage()}</p>
            </div>

            {/* Error Display */}
            {generationError && (
              <div className="flex items-start space-x-3 bg-red-50 border border-red-200 rounded-lg p-4">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-900">Generation Error</p>
                  <p className="text-sm text-red-700 mt-1">{generationError}</p>
                </div>
                <button
                  onClick={resetWorkflow}
                  className="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-800 rounded text-sm font-medium"
                >
                  Start Over
                </button>
              </div>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
              <p><strong>This may take 5-15 minutes depending on quality tier.</strong></p>
              <p className="mt-2">You can leave this page - the generation will continue in the background!</p>
            </div>
          </div>
        )}

        {/* Stage 4: Complete */}
        {currentStage === 'complete' && (
          <div className="space-y-6 text-center">
            <div className="flex items-center justify-center space-x-3">
              <CheckCircle className="w-12 h-12 text-green-500" />
              <h2 className="text-2xl font-semibold text-gray-800">
                Animation Complete!
              </h2>
            </div>

            {videoUrl && (
              <div className="space-y-4">
                <video
                  controls
                  className="w-full max-w-3xl mx-auto rounded-lg shadow-lg"
                  src={`${apiUrl}${videoUrl}`}
                >
                  Your browser does not support video playback.
                </video>

                <button
                  onClick={downloadVideo}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors flex items-center justify-center space-x-2 mx-auto"
                >
                  <Download className="w-5 h-5" />
                  <span>Download Video</span>
                </button>
              </div>
            )}

            <button
              onClick={resetWorkflow}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
            >
              Create Another Animation
            </button>
          </div>
        )}
      </div>

      {/* Info Footer */}
      <div className="text-center text-xs text-gray-500">
        <p>BeatCanvas Animation Workflow - Powered by SDXL, ControlNet, and Multi-LoRA Technology</p>
      </div>
    </div>
  );
};

export default AnimationVideoGenerator;
