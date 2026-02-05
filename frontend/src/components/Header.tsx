import React from 'react';
import { Music, Video, Palette } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <header className="bg-dark-800 border-b border-dark-600 shadow-lg">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Music className="h-8 w-8 text-primary-500" />
                <Video className="h-4 w-4 text-primary-400 absolute -top-1 -right-1" />
              </div>
              <h1 className="text-3xl font-bold text-white">BeatCanvas</h1>
            </div>
            <div className="hidden md:flex items-center space-x-1 text-dark-300">
              <Palette className="h-4 w-4" />
              <span className="text-sm">AI Music Video Generator</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden md:flex items-center space-x-6 text-sm text-dark-300">
              <span>Multi-Provider Image Generation</span>
              <span>•</span>
              <span>Real-time Editing</span>
              <span>•</span>
              <span>Professional Output</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;