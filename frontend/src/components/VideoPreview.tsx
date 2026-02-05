import React, { useState, useEffect } from 'react';
import { Download, Play, Pause, Volume2, VolumeX, Maximize2, ExternalLink } from 'lucide-react';
import InteractiveTimeline from './InteractiveTimeline';

interface StoryboardScene {
  timestamp_start: number;
  timestamp_end: number;
  description: string;
  mood: string;
  effects: string[];
  visual_style?: string;
  camera_direction?: string;
}

interface VideoPreviewProps {
  videoUrl: string;
  storyboard: StoryboardScene[];
  onDownload: () => void;
  onSceneEdit: (sceneIndex: number) => void;
  editingSceneIndex?: number;
}

const VideoPreview: React.FC<VideoPreviewProps> = ({
  videoUrl,
  storyboard,
  onDownload,
  onSceneEdit,
  editingSceneIndex
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [videoRef, setVideoRef] = useState<HTMLVideoElement | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);

  const togglePlay = () => {
    if (videoRef) {
      if (isPlaying) {
        videoRef.pause();
      } else {
        videoRef.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef) {
      videoRef.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const toggleFullscreen = () => {
    if (videoRef) {
      if (videoRef.requestFullscreen) {
        videoRef.requestFullscreen();
      }
    }
  };

  const handleVideoEnd = () => {
    setIsPlaying(false);
  };

  // Handle video time updates
  const handleTimeUpdate = () => {
    if (videoRef) {
      setCurrentTime(videoRef.currentTime);
    }
  };

  // Handle video metadata loaded
  const handleLoadedMetadata = () => {
    if (videoRef) {
      setVideoDuration(videoRef.duration);
    }
  };

  // Handle seek from timeline
  const handleSeek = (time: number) => {
    if (videoRef) {
      videoRef.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Setup video event listeners
  useEffect(() => {
    if (videoRef) {
      videoRef.addEventListener('timeupdate', handleTimeUpdate);
      videoRef.addEventListener('loadedmetadata', handleLoadedMetadata);

      return () => {
        videoRef.removeEventListener('timeupdate', handleTimeUpdate);
        videoRef.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    }
  }, [videoRef]);

  return (
    <div className="bg-dark-700 rounded-xl border border-dark-600 overflow-hidden">
      <div className="p-6 border-b border-dark-600">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white flex items-center">
            <Play className="h-5 w-5 mr-2" />
            Your Music Video
          </h2>

          <div className="flex space-x-2">
            <button
              onClick={onDownload}
              className="flex items-center space-x-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>Download</span>
            </button>

            <button
              onClick={() => window.open(videoUrl, '_blank')}
              className="p-2 text-dark-400 hover:text-white border border-dark-500 rounded-lg hover:border-dark-400 transition-colors"
              title="Open in new tab"
            >
              <ExternalLink className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="relative group">
        {/* Video Player */}
        <video
          ref={setVideoRef}
          src={videoUrl}
          className="w-full aspect-video bg-black"
          onEnded={handleVideoEnd}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1792 1024'%3E%3Crect width='1792' height='1024' fill='%23111827'/%3E%3C/svg%3E"
        />

        {/* Video Controls Overlay */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200">
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <div className="flex items-center space-x-4">
              <button
                onClick={togglePlay}
                className="p-4 bg-black bg-opacity-70 text-white rounded-full hover:bg-opacity-90 transition-all"
              >
                {isPlaying ? (
                  <Pause className="h-8 w-8" />
                ) : (
                  <Play className="h-8 w-8" />
                )}
              </button>
            </div>
          </div>

          {/* Bottom Controls */}
          <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                className="p-2 bg-black bg-opacity-70 text-white rounded hover:bg-opacity-90 transition-all"
              >
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </button>
            </div>

            <button
              onClick={toggleFullscreen}
              className="p-2 bg-black bg-opacity-70 text-white rounded hover:bg-opacity-90 transition-all"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Timeline */}
      {storyboard && storyboard.length > 0 && (
        <div className="p-6 border-b border-dark-600">
          <InteractiveTimeline
            storyboard={storyboard}
            videoDuration={videoDuration}
            currentTime={currentTime}
            onSeek={handleSeek}
            onSceneEdit={onSceneEdit}
            editingSceneIndex={editingSceneIndex}
          />
        </div>
      )}

      {/* Video Info */}
      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className="text-dark-400 mb-1">Resolution</div>
            <div className="text-white font-medium">1792×1024</div>
          </div>
          <div className="text-center">
            <div className="text-dark-400 mb-1">Format</div>
            <div className="text-white font-medium">MP4</div>
          </div>
          <div className="text-center">
            <div className="text-dark-400 mb-1">Frame Rate</div>
            <div className="text-white font-medium">24 FPS</div>
          </div>
          <div className="text-center">
            <div className="text-dark-400 mb-1">Quality</div>
            <div className="text-white font-medium">HD</div>
          </div>
        </div>

        {/* Success Message */}
        <div className="mt-6 p-4 bg-green-900/20 border border-green-700 rounded-lg">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <p className="text-green-400 text-sm font-medium">
              Video generated successfully!
            </p>
          </div>
          <p className="text-green-200 text-sm mt-1">
            Your music video is ready to download and share.
          </p>
        </div>

        {/* Sharing Options */}
        <div className="mt-4 pt-4 border-t border-dark-600">
          <div className="text-sm text-dark-400 mb-2">Share your creation:</div>
          <div className="text-xs text-dark-500">
            • High-quality MP4 file suitable for all platforms
            • 16:9 aspect ratio perfect for YouTube, social media
            • Professional-grade audio-visual synchronization
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPreview;