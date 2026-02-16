import React, { useState } from 'react';
import VideoGenerator from './components/VideoGenerator';
import AnimationVideoGenerator from './components/AnimationVideoGenerator';
import Header from './components/Header';
import { Film, Wand2 } from 'lucide-react';

type Mode = 'storyboard' | 'animation';

function App() {
  const [mode, setMode] = useState<Mode>('storyboard');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Header />

      {/* Mode Selector */}
      <div className="container mx-auto px-4 pt-6">
        <div className="flex justify-center space-x-4 mb-6">
          <button
            onClick={() => setMode('storyboard')}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all ${
              mode === 'storyboard'
                ? 'bg-purple-600 text-white shadow-lg'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
            }`}
          >
            <Film className="w-5 h-5" />
            <span>Storyboard Workflow</span>
          </button>
          <button
            onClick={() => setMode('animation')}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all ${
              mode === 'animation'
                ? 'bg-purple-600 text-white shadow-lg'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
            }`}
          >
            <Wand2 className="w-5 h-5" />
            <span>Animation Workflow</span>
            <span className="ml-2 px-2 py-0.5 bg-green-400 text-green-900 text-xs rounded-full font-bold">
              NEW
            </span>
          </button>
        </div>

        {/* Mode Description */}
        <div className="max-w-3xl mx-auto mb-8">
          {mode === 'storyboard' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-900">
              <strong>Storyboard Workflow:</strong> Create detailed scene-by-scene videos with full editing control.
              Perfect for narrative music videos with specific visual requirements.
            </div>
          )}
          {mode === 'animation' && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-sm text-purple-900">
              <strong>Animation Workflow:</strong> Transform your music into stunning animated videos using
              16 non-photorealistic styles. Perfect for artistic music videos, character-driven content, and
              unique visual aesthetics. Supports custom character LoRAs for consistent character appearances.
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 pb-8">
        {mode === 'storyboard' && <VideoGenerator />}
        {mode === 'animation' && <AnimationVideoGenerator />}
      </main>
    </div>
  );
}

export default App;
