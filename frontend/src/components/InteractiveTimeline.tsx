import React, { useEffect, useRef, useState } from 'react';

interface StoryboardScene {
  timestamp_start: number;
  timestamp_end: number;
  description: string;
  mood: string;
  effects: string[];
  visual_style?: string;
  camera_direction?: string;
}

interface TimelineProps {
  storyboard: StoryboardScene[];
  videoDuration: number;
  currentTime: number;
  onSeek: (time: number) => void;
  onSceneEdit: (sceneIndex: number) => void;
  editingSceneIndex?: number;
}

const MOOD_COLORS = {
  energetic: '#ef4444', // red
  calm: '#3b82f6',      // blue
  dark: '#374151',      // gray
  bright: '#fbbf24',    // yellow
  neutral: '#6b7280',   // gray-500
  intense: '#dc2626',   // red-600
  peaceful: '#10b981',  // emerald
  dramatic: '#7c3aed',  // violet
  romantic: '#ec4899',  // pink
  mysterious: '#1f2937' // gray-800
} as const;

const getMoodColor = (mood: string): string => {
  const normalizedMood = mood.toLowerCase();
  for (const [key, color] of Object.entries(MOOD_COLORS)) {
    if (normalizedMood.includes(key)) {
      return color;
    }
  }
  return MOOD_COLORS.neutral;
};

const InteractiveTimeline: React.FC<TimelineProps> = ({
  storyboard,
  videoDuration,
  currentTime,
  onSeek,
  onSceneEdit,
  editingSceneIndex
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoveredScene, setHoveredScene] = useState<number | null>(null);

  // Calculate timeline dimensions
  const timelineWidth = 100; // percentage
  const sceneCount = storyboard.length;

  // Handle click on timeline to seek
  const handleTimelineClick = (event: React.MouseEvent) => {
    if (!timelineRef.current) return;

    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickPosition = clickX / rect.width;
    const seekTime = clickPosition * videoDuration;

    onSeek(seekTime);
  };

  // Handle scene segment click
  const handleSceneClick = (sceneIndex: number, event: React.MouseEvent) => {
    event.stopPropagation();
    const scene = storyboard[sceneIndex];
    onSeek(scene.timestamp_start);
  };

  // Handle scene double-click for editing
  const handleSceneDoubleClick = (sceneIndex: number, event: React.MouseEvent) => {
    event.stopPropagation();
    onSceneEdit(sceneIndex);
  };

  // Calculate playhead position
  const playheadPosition = (currentTime / videoDuration) * 100;

  // Find active scene based on current time
  const activeSceneIndex = storyboard.findIndex(scene =>
    currentTime >= scene.timestamp_start && currentTime <= scene.timestamp_end
  );

  // Format time display
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full bg-gray-900 rounded-lg p-4 border border-gray-700">
      {/* Timeline Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="text-white font-medium text-sm">
          Timeline ({sceneCount} scenes)
        </div>
        <div className="text-gray-400 text-sm">
          {formatTime(currentTime)} / {formatTime(videoDuration)}
        </div>
      </div>

      {/* Main Timeline Container */}
      <div className="relative">
        {/* Timeline Track */}
        <div
          ref={timelineRef}
          className="relative h-16 bg-gray-800 rounded cursor-pointer border border-gray-600"
          onClick={handleTimelineClick}
        >
          {/* Scene Segments */}
          {storyboard.map((scene, index) => {
            const startPercent = (scene.timestamp_start / videoDuration) * 100;
            const widthPercent = ((scene.timestamp_end - scene.timestamp_start) / videoDuration) * 100;
            const isActive = index === activeSceneIndex;
            const isEditing = index === editingSceneIndex;
            const isHovered = index === hoveredScene;

            return (
              <div
                key={index}
                className={`absolute top-0 h-full border-r border-gray-700 last:border-r-0 cursor-pointer transition-all duration-200 ${
                  isActive ? 'ring-2 ring-blue-400' : ''
                } ${
                  isEditing ? 'ring-2 ring-purple-400' : ''
                } ${
                  isHovered ? 'brightness-125' : ''
                }`}
                style={{
                  left: `${startPercent}%`,
                  width: `${widthPercent}%`,
                  backgroundColor: getMoodColor(scene.mood),
                  opacity: isActive ? 0.9 : 0.7
                }}
                onClick={(e) => handleSceneClick(index, e)}
                onDoubleClick={(e) => handleSceneDoubleClick(index, e)}
                onMouseEnter={() => setHoveredScene(index)}
                onMouseLeave={() => setHoveredScene(null)}
                title={`Scene ${index + 1}: ${scene.description} (${formatTime(scene.timestamp_start)} - ${formatTime(scene.timestamp_end)})`}
              >
                {/* Scene Number Label (only show on larger segments) */}
                {widthPercent > 3 && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-white text-xs font-medium">
                      {index + 1}
                    </span>
                  </div>
                )}

                {/* Edit Indicator */}
                {isEditing && (
                  <div className="absolute top-0 right-0 w-2 h-2 bg-purple-400 rounded-bl-md">
                    <div className="absolute -top-1 -right-1 w-1 h-1 bg-purple-400 rounded-full animate-pulse" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Playhead */}
          <div
            className="absolute top-0 h-full w-0.5 bg-white z-10 pointer-events-none"
            style={{ left: `${playheadPosition}%` }}
          >
            {/* Playhead Handle */}
            <div className="absolute -top-1 -left-2 w-4 h-4 bg-white rounded-full border-2 border-blue-500 shadow-lg" />
          </div>
        </div>

        {/* Scene Info Display */}
        {hoveredScene !== null && (
          <div className="absolute top-20 left-0 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg z-20 min-w-64 max-w-sm">
            <div className="text-white font-medium text-sm mb-1">
              Scene {hoveredScene + 1}
            </div>
            <div className="text-gray-300 text-xs mb-2">
              {formatTime(storyboard[hoveredScene].timestamp_start)} - {formatTime(storyboard[hoveredScene].timestamp_end)}
              {' '}({formatTime(storyboard[hoveredScene].timestamp_end - storyboard[hoveredScene].timestamp_start)} duration)
            </div>
            <div className="text-gray-300 text-xs mb-2">
              <strong>Description:</strong> {storyboard[hoveredScene].description}
            </div>
            <div className="flex items-center justify-between">
              <div className="text-gray-400 text-xs">
                <strong>Mood:</strong> {storyboard[hoveredScene].mood}
              </div>
              <div className="text-gray-400 text-xs">
                Double-click to edit
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Timeline Controls */}
      <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-blue-400 rounded"></div>
            <span>Current scene</span>
          </div>
          {editingSceneIndex !== undefined && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-purple-400 rounded"></div>
              <span>Editing scene</span>
            </div>
          )}
        </div>
        <div className="text-gray-500">
          Click to seek • Double-click scene to edit
        </div>
      </div>
    </div>
  );
};

export default InteractiveTimeline;