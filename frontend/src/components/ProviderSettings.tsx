import React from 'react';
import { Bot, Palette, Zap, Star } from 'lucide-react';

interface ProviderSettingsProps {
  qualityTier: string;
  onQualityChange: (tier: string) => void;
  providerPreference: 'auto' | 'dalle' | 'novelai' | 'both';
  onProviderChange: (provider: 'auto' | 'dalle' | 'novelai' | 'both') => void;
}

const ProviderSettings: React.FC<ProviderSettingsProps> = ({
  qualityTier,
  onQualityChange,
  providerPreference,
  onProviderChange
}) => {
  const qualityOptions = [
    {
      id: 'basic',
      name: 'Basic',
      description: '12 scenes • $2-4',
      icon: Zap,
      scenes: '12 scenes',
      cost: '$2-4'
    },
    {
      id: 'professional',
      name: 'Professional',
      description: '24 scenes • $4-6',
      icon: Star,
      scenes: '24 scenes',
      cost: '$4-6',
      recommended: true
    },
    {
      id: 'cinematic',
      name: 'Cinematic',
      description: '48 scenes • $6-9',
      icon: Bot,
      scenes: '48 scenes',
      cost: '$6-9'
    }
  ];

  const providerOptions = [
    {
      id: 'auto',
      name: 'Smart Selection',
      description: 'Automatically choose the best provider for each scene',
      icon: Bot,
      details: 'Photorealistic → DALL-E • Artistic → NovelAI'
    },
    {
      id: 'dalle',
      name: 'DALL-E 3',
      description: 'Best for photorealistic and consistent results',
      icon: Palette,
      details: 'OpenAI • $0.04 per image • Excellent prompt following'
    },
    {
      id: 'novelai',
      name: 'NovelAI',
      description: 'Best for artistic and anime-style content',
      icon: Palette,
      details: 'NovelAI • $0.03 per image • Superior character consistency'
    },
    {
      id: 'both',
      name: 'Both Providers',
      description: 'Generate with both providers for maximum options',
      icon: Star,
      details: 'Double the variations • Higher cost • Maximum flexibility'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Quality Tier Selection */}
      <div>
        <label className="block text-sm font-medium text-white mb-3">
          Quality Level
        </label>
        <div className="grid grid-cols-1 gap-3">
          {qualityOptions.map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.id}
                onClick={() => onQualityChange(option.id)}
                className={`relative p-4 border rounded-lg text-left transition-all duration-200 ${
                  qualityTier === option.id
                    ? 'border-primary-500 bg-primary-900/20'
                    : 'border-dark-500 bg-dark-800/50 hover:border-dark-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-5 w-5 ${
                      qualityTier === option.id ? 'text-primary-400' : 'text-dark-400'
                    }`} />
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-white">{option.name}</span>
                        {option.recommended && (
                          <span className="px-2 py-0.5 text-xs bg-primary-500 text-white rounded-full">
                            Recommended
                          </span>
                        )}
                      </div>
                      <span className="text-sm text-dark-300">{option.description}</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Provider Selection */}
      <div>
        <label className="block text-sm font-medium text-white mb-3">
          Image Generation Provider
        </label>
        <div className="grid grid-cols-1 gap-3">
          {providerOptions.map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.id}
                onClick={() => onProviderChange(option.id as any)}
                className={`relative p-4 border rounded-lg text-left transition-all duration-200 ${
                  providerPreference === option.id
                    ? 'border-primary-500 bg-primary-900/20'
                    : 'border-dark-500 bg-dark-800/50 hover:border-dark-400'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <Icon className={`h-5 w-5 mt-0.5 ${
                    providerPreference === option.id ? 'text-primary-400' : 'text-dark-400'
                  }`} />
                  <div className="flex-1">
                    <div className="font-medium text-white">{option.name}</div>
                    <div className="text-sm text-dark-300 mb-1">{option.description}</div>
                    <div className="text-xs text-dark-400">{option.details}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="p-4 bg-dark-800 border border-dark-600 rounded-lg">
        <h4 className="text-sm font-medium text-white mb-2">Cost Estimate</h4>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between text-dark-300">
            <span>Concept Generation (GPT-4)</span>
            <span>$0.15</span>
          </div>
          <div className="flex justify-between text-dark-300">
            <span>
              Image Generation ({qualityOptions.find(q => q.id === qualityTier)?.scenes || '24 scenes'})
            </span>
            <span>
              {providerPreference === 'both' ? '$3.36-5.76' :
               providerPreference === 'novelai' ? '$1.80-3.60' : '$2.88-5.76'}
            </span>
          </div>
          <div className="flex justify-between text-dark-300">
            <span>Video Processing</span>
            <span>Free</span>
          </div>
          <hr className="border-dark-600 my-2" />
          <div className="flex justify-between text-white font-medium">
            <span>Total</span>
            <span>
              {providerPreference === 'both' ? '$3.51-5.91' :
               providerPreference === 'novelai' ? '$1.95-3.75' : '$3.03-5.91'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProviderSettings;