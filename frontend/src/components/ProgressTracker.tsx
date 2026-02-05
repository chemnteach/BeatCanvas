import React from 'react';
import { CheckCircle, AlertCircle, Loader2, Music, Palette, Film, Video } from 'lucide-react';

interface ProgressTrackerProps {
  progress: string;
  status: 'started' | 'complete' | 'error';
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({ progress, status }) => {
  const getProgressSteps = () => {
    const steps = [
      {
        id: 'audio',
        label: 'Analyzing Music',
        icon: Music,
        keywords: ['analyzing', 'audio', 'music']
      },
      {
        id: 'concept',
        label: 'Generating Concept',
        icon: Palette,
        keywords: ['concept', 'visual', 'generating']
      },
      {
        id: 'storyboard',
        label: 'Creating Storyboard',
        icon: Film,
        keywords: ['storyboard', 'creating', 'scenes']
      },
      {
        id: 'images',
        label: 'Generating Images',
        icon: Palette,
        keywords: ['images', 'generating', 'dall-e', 'novelai']
      },
      {
        id: 'video',
        label: 'Assembling Video',
        icon: Video,
        keywords: ['assembling', 'video', 'rendering']
      }
    ];

    const progressLower = progress.toLowerCase();
    let currentStepIndex = -1;

    // Find current step based on progress message
    for (let i = 0; i < steps.length; i++) {
      if (steps[i].keywords.some(keyword => progressLower.includes(keyword))) {
        currentStepIndex = i;
        break;
      }
    }

    // If complete, all steps are done
    if (status === 'complete') {
      currentStepIndex = steps.length;
    }

    return steps.map((step, index) => ({
      ...step,
      status: index < currentStepIndex ? 'completed' :
              index === currentStepIndex ? 'current' :
              'pending'
    }));
  };

  const steps = getProgressSteps();

  const getStepIcon = (step: any) => {
    const IconComponent = step.icon;

    if (step.status === 'completed') {
      return <CheckCircle className="h-5 w-5 text-green-400" />;
    } else if (step.status === 'current') {
      return <Loader2 className="h-5 w-5 text-primary-400 animate-spin" />;
    } else {
      return <IconComponent className="h-5 w-5 text-dark-500" />;
    }
  };

  return (
    <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Generation Progress</h2>

        {status === 'error' && (
          <div className="flex items-center space-x-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm">Error</span>
          </div>
        )}

        {status === 'complete' && (
          <div className="flex items-center space-x-2 text-green-400">
            <CheckCircle className="h-5 w-5" />
            <span className="text-sm">Complete</span>
          </div>
        )}
      </div>

      {/* Progress Steps */}
      <div className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              {getStepIcon(step)}
            </div>

            <div className="flex-1">
              <div className={`text-sm font-medium ${
                step.status === 'completed' ? 'text-green-400' :
                step.status === 'current' ? 'text-primary-400' :
                'text-dark-400'
              }`}>
                {step.label}
              </div>

              {/* Progress bar for current step */}
              {step.status === 'current' && (
                <div className="mt-1">
                  <div className="h-1 bg-dark-600 rounded-full overflow-hidden">
                    <div className="h-full bg-primary-400 rounded-full animate-pulse w-3/4"></div>
                  </div>
                </div>
              )}
            </div>

            {/* Connection line */}
            {index < steps.length - 1 && (
              <div className={`absolute left-2.5 mt-8 h-6 w-px ${
                step.status === 'completed' ? 'bg-green-400' : 'bg-dark-600'
              }`}></div>
            )}
          </div>
        ))}
      </div>

      {/* Current Progress Message */}
      <div className="mt-6 p-3 bg-dark-800 rounded-lg border border-dark-600">
        <p className="text-sm text-dark-200">{progress}</p>
      </div>

      {/* Estimated Time Remaining */}
      {status === 'started' && (
        <div className="mt-4 text-xs text-dark-400 text-center">
          Estimated time remaining: 2-5 minutes
        </div>
      )}
    </div>
  );
};

export default ProgressTracker;