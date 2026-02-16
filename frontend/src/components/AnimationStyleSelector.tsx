import React, { useState, useEffect } from 'react';
import { Palette, Info } from 'lucide-react';

interface AnimationStyle {
  name: string;
  display_name: string;
  description: string;
  best_for: string;
  guidance_scale: number;
  conditioning_scale: number;
}

interface AnimationStylesResponse {
  total_styles: number;
  styles: AnimationStyle[];
  categories: {
    [key: string]: string[];
  };
}

interface AnimationStyleSelectorProps {
  selectedStyle: string;
  onStyleSelect: (style: string) => void;
  apiUrl?: string;
}

const AnimationStyleSelector: React.FC<AnimationStyleSelectorProps> = ({
  selectedStyle,
  onStyleSelect,
  apiUrl = 'http://localhost:8000'
}) => {
  const [styles, setStyles] = useState<AnimationStyle[]>([]);
  const [categories, setCategories] = useState<{ [key: string]: string[] }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    fetchAnimationStyles();
  }, []);

  const fetchAnimationStyles = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/animation/styles`);

      if (!response.ok) {
        throw new Error('Failed to fetch animation styles');
      }

      const data: AnimationStylesResponse = await response.json();
      setStyles(data.styles);
      setCategories(data.categories);
      setError(null);
    } catch (err) {
      console.error('Error fetching animation styles:', err);
      setError('Failed to load animation styles. Using defaults.');

      // Fallback to basic styles
      setStyles([
        {
          name: 'watercolor',
          display_name: 'Watercolor',
          description: 'Soft brush strokes, warm tones, dreamy atmosphere',
          best_for: 'Romantic, soft rock, indie folk, tropical vibes',
          guidance_scale: 8.0,
          conditioning_scale: 0.7
        },
        {
          name: 'cel_shaded',
          display_name: 'Cel Shaded',
          description: 'Flat colors, clean outlines, anime-style',
          best_for: 'Upbeat pop, energetic rock, summery vibes',
          guidance_scale: 7.5,
          conditioning_scale: 0.75
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getStylesByCategory = (category: string): AnimationStyle[] => {
    if (category === 'all') return styles;

    const categoryStyles = categories[category] || [];
    return styles.filter(style => categoryStyles.includes(style.name));
  };

  const categoryNames: { [key: string]: string } = {
    all: 'All Styles',
    tropical: 'Tropical / Beach / Trop Rock',
    rock: 'Rock / Alternative / Punk',
    electronic: 'Electronic / EDM / Synthwave',
    jazz_classical: 'Jazz / Classical / Sophisticated',
    world_indie: 'World / Indie / Folk',
    pop: 'Pop / Radio-Friendly'
  };

  const currentStyles = getStylesByCategory(selectedCategory);
  const selectedStyleObj = styles.find(s => s.name === selectedStyle);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <span className="ml-3 text-gray-600">Loading animation styles...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-2">
        <Palette className="w-5 h-5 text-purple-600" />
        <h3 className="text-lg font-semibold text-gray-800">Animation Style</h3>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
          {error}
        </div>
      )}

      {/* Category Filter */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Filter by Genre
        </label>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        >
          {Object.entries(categoryNames).map(([key, label]) => (
            <option key={key} value={key}>
              {label} ({key === 'all' ? styles.length : (categories[key]?.length || 0)} styles)
            </option>
          ))}
        </select>
      </div>

      {/* Style Selection */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Choose Animation Style
        </label>
        <select
          value={selectedStyle}
          onChange={(e) => onStyleSelect(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        >
          <option value="">Select a style...</option>
          {currentStyles.map((style) => (
            <option key={style.name} value={style.name}>
              {style.display_name}
            </option>
          ))}
        </select>
      </div>

      {/* Style Details */}
      {selectedStyleObj && (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4 space-y-3">
          <div className="flex items-start space-x-2">
            <Info className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
            <div className="space-y-2">
              <h4 className="font-semibold text-purple-900">{selectedStyleObj.display_name}</h4>
              <p className="text-sm text-gray-700">
                <strong>Look:</strong> {selectedStyleObj.description}
              </p>
              <p className="text-sm text-gray-700">
                <strong>Best for:</strong> {selectedStyleObj.best_for}
              </p>
              <div className="flex space-x-4 text-xs text-gray-600 mt-2">
                <span>Guidance: {selectedStyleObj.guidance_scale}</span>
                <span>Conditioning: {selectedStyleObj.conditioning_scale}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Style Count */}
      <div className="text-xs text-gray-500 text-center">
        {currentStyles.length} {currentStyles.length === 1 ? 'style' : 'styles'} available
        {selectedCategory !== 'all' && ` in ${categoryNames[selectedCategory]}`}
      </div>
    </div>
  );
};

export default AnimationStyleSelector;
