import React, { useState } from 'react';
import { Settings, Globe, Eye, Shield, AlertTriangle } from 'lucide-react';

interface CulturalContentSettingsProps {
  onSettingsChange: (settings: CulturalSettings) => void;
  isVisible: boolean;
  onClose: () => void;
}

interface CulturalSettings {
  standard: 'american' | 'european' | 'conservative';
  requireUserApproval: boolean;
  processAfterGeneration: boolean;
  sceneContexts: string[];
}

const CulturalContentSettings: React.FC<CulturalContentSettingsProps> = ({
  onSettingsChange,
  isVisible,
  onClose
}) => {
  const [settings, setSettings] = useState<CulturalSettings>({
    standard: 'american',
    requireUserApproval: true,
    processAfterGeneration: true,
    sceneContexts: []
  });

  const [showAdvanced, setShowAdvanced] = useState(false);

  const culturalStandards = [
    {
      id: 'american',
      name: 'American Standards',
      description: 'Platform-compliant content suitable for American audiences',
      icon: '🇺🇸',
      details: [
        'Beach scenes: Bikini minimum required',
        'Artistic content: Covering or blurring applied',
        'Family-friendly approach',
        'Platform advertising compliant'
      ]
    },
    {
      id: 'european',
      name: 'European Standards',
      description: 'Cultural content normal for European beaches and art',
      icon: '🇪🇺',
      details: [
        'Beach scenes: Natural appearance accepted',
        'Urban scenes: Amsterdam-style billboards/ads acceptable',
        'Home scenes: Natural domestic comfort respected',
        'Artistic content: European cultural expression protected',
        'Fashion/Commercial: European advertising norms applied'
      ]
    },
    {
      id: 'conservative',
      name: 'Conservative Standards',
      description: 'Family-oriented content with modest presentation',
      icon: '👨‍👩‍👧‍👦',
      details: [
        'Beach scenes: Full coverage required',
        'Artistic content: Family-appropriate only',
        'Modest dress emphasized',
        'Traditional values respected'
      ]
    }
  ];

  const handleStandardChange = (standard: 'american' | 'european' | 'conservative') => {
    const newSettings = {
      ...settings,
      standard,
      // Auto-adjust approval requirement based on standard
      requireUserApproval: standard === 'european' ? true : settings.requireUserApproval
    };

    setSettings(newSettings);
    onSettingsChange(newSettings);
  };

  const handleSettingChange = (key: keyof CulturalSettings, value: any) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    onSettingsChange(newSettings);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Globe className="h-6 w-6 text-blue-400" />
            <div>
              <h2 className="text-xl font-semibold text-white">
                Cultural Content Settings
              </h2>
              <p className="text-gray-400 text-sm">
                Configure content processing for different cultural markets
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[70vh] overflow-y-auto space-y-6">
          {/* Cultural Standard Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-3">
              Cultural Standard
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {culturalStandards.map((standard) => (
                <div
                  key={standard.id}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    settings.standard === standard.id
                      ? 'bg-blue-600 border-blue-500'
                      : 'bg-gray-800 border-gray-600 hover:bg-gray-700'
                  }`}
                  onClick={() => handleStandardChange(standard.id as any)}
                >
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-2xl">{standard.icon}</span>
                    <div>
                      <h3 className="font-medium text-white">{standard.name}</h3>
                    </div>
                  </div>
                  <p className="text-sm text-gray-300 mb-3">
                    {standard.description}
                  </p>
                  <ul className="text-xs text-gray-400 space-y-1">
                    {standard.details.map((detail, idx) => (
                      <li key={idx}>• {detail}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          {/* Processing Options */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-white flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>Processing Options</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* User Approval */}
              <div className="bg-gray-800 rounded-lg p-4">
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <div className="font-medium text-white">Require User Approval</div>
                    <div className="text-sm text-gray-400">
                      Review modifications before applying
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.requireUserApproval}
                    onChange={(e) => handleSettingChange('requireUserApproval', e.target.checked)}
                    className="w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                </label>
              </div>

              {/* Auto Processing */}
              <div className="bg-gray-800 rounded-lg p-4">
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <div className="font-medium text-white">Process After Generation</div>
                    <div className="text-sm text-gray-400">
                      Automatically analyze generated content
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.processAfterGeneration}
                    onChange={(e) => handleSettingChange('processAfterGeneration', e.target.checked)}
                    className="w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                </label>
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2 text-blue-400 hover:text-blue-300 transition-colors"
            >
              <Settings className="h-4 w-4" />
              <span>Advanced Options</span>
              <span className="text-xs">({showAdvanced ? 'Hide' : 'Show'})</span>
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-4">
                {/* Scene Context Configuration */}
                <div className="bg-gray-800 rounded-lg p-4">
                  <h4 className="font-medium text-white mb-2">Scene Context Hints</h4>
                  <p className="text-sm text-gray-400 mb-3">
                    Provide context to improve cultural processing accuracy
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-300 w-20">Beach:</span>
                      <input
                        type="text"
                        placeholder="e.g., Barcelona beach scene, Mediterranean setting"
                        className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-300 w-20">Urban:</span>
                      <input
                        type="text"
                        placeholder="e.g., Amsterdam street scene, European city billboard"
                        className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-300 w-20">Home:</span>
                      <input
                        type="text"
                        placeholder="e.g., Private domestic scene, European home culture"
                        className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-300 w-20">Artistic:</span>
                      <input
                        type="text"
                        placeholder="e.g., Classical art reference, Renaissance style"
                        className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Privacy Information */}
                <div className="bg-gray-800 rounded-lg p-4">
                  <h4 className="font-medium text-white mb-2 flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-green-400" />
                    <span>Privacy & Processing</span>
                  </h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>• All processing occurs locally on your machine</li>
                    <li>• No images are uploaded to external services</li>
                    <li>• Original files are preserved for rollback</li>
                    <li>• Processing is completely private and secure</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Important Disclaimers */}
          <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-yellow-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-yellow-400 mb-2">Important Legal Notice</h4>
                <ul className="text-sm text-yellow-300 space-y-1">
                  <li>• Users are responsible for compliance with local laws and regulations</li>
                  <li>• Content should always respect consent and age-appropriate standards</li>
                  <li>• Professional and tasteful presentation is maintained across all standards</li>
                  <li>• This tool assists with cultural adaptation, not inappropriate content creation</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Technical Information */}
          <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <Eye className="h-5 w-5 text-blue-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-blue-400 mb-2">How It Works</h4>
                <ul className="text-sm text-blue-300 space-y-1">
                  <li>• Computer vision analyzes generated images for content</li>
                  <li>• Cultural rules determine if modifications are appropriate</li>
                  <li>• Local image processing applies tasteful adjustments</li>
                  <li>• User approval ensures control over all changes</li>
                  <li>• Original AI-generated images are always preserved</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-400">
            Current: <span className="text-white font-medium">
              {culturalStandards.find(s => s.id === settings.standard)?.name}
            </span>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:text-white border border-gray-600 rounded-lg hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Apply Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CulturalContentSettings;