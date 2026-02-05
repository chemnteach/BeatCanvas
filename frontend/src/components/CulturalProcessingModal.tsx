import React, { useState, useEffect } from 'react';
import { Eye, Check, X, AlertTriangle, Globe, Shield, Download } from 'lucide-react';
import axios from 'axios';

interface ProcessingResult {
  original_path: string;
  modified_path: string;
  modifications_applied: string[];
  confidence: number;
  description: string;
  user_approval_required: boolean;
}

interface ProcessingReport {
  total_scenes: number;
  modified_scenes: number;
  modification_rate: number;
  modifications_by_type: Record<string, number>;
  high_confidence_modifications: number;
  user_approval_required: number;
}

interface CulturalProcessingModalProps {
  isOpen: boolean;
  taskId: string;
  culturalStandard: string;
  onClose: () => void;
  onProcessingComplete: (modifiedPaths: string[]) => void;
}

const CulturalProcessingModal: React.FC<CulturalProcessingModalProps> = ({
  isOpen,
  taskId,
  culturalStandard,
  onClose,
  onProcessingComplete
}) => {
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<ProcessingResult[]>([]);
  const [report, setReport] = useState<ProcessingReport | null>(null);
  const [selectedScenes, setSelectedScenes] = useState<Set<number>>(new Set());
  const [step, setStep] = useState<'analyze' | 'review' | 'apply' | 'complete'>('analyze');

  useEffect(() => {
    if (isOpen && taskId) {
      startProcessing();
    }
  }, [isOpen, taskId]);

  const startProcessing = async () => {
    setProcessing(true);
    setStep('analyze');

    try {
      const response = await axios.post('/api/process-cultural-content', {
        task_id: taskId,
        cultural_standard: culturalStandard,
        scene_contexts: [],
        require_user_approval: true
      });

      setResults(response.data.results);
      setReport(response.data.processing_report);

      // Auto-select scenes that need approval
      const needApproval = new Set<number>();
      response.data.results.forEach((result: ProcessingResult, index: number) => {
        if (result.user_approval_required) {
          needApproval.add(index);
        }
      });
      setSelectedScenes(needApproval);

      setStep('review');
    } catch (error) {
      console.error('Cultural processing failed:', error);
    } finally {
      setProcessing(false);
    }
  };

  const handleApproveSelected = async () => {
    setProcessing(true);
    setStep('apply');

    try {
      const approvedIndices = Array.from(selectedScenes);
      await axios.post(`/api/approve-cultural-modifications`, {
        task_id: taskId,
        approved_scenes: approvedIndices
      });

      const modifiedPaths = results
        .filter((_, index) => selectedScenes.has(index))
        .map(result => result.modified_path);

      setStep('complete');
      onProcessingComplete(modifiedPaths);
    } catch (error) {
      console.error('Failed to apply modifications:', error);
    } finally {
      setProcessing(false);
    }
  };

  const toggleSceneSelection = (index: number) => {
    const newSelection = new Set(selectedScenes);
    if (newSelection.has(index)) {
      newSelection.delete(index);
    } else {
      newSelection.add(index);
    }
    setSelectedScenes(newSelection);
  };

  const getStandardInfo = (standard: string) => {
    const info = {
      american: { flag: '🇺🇸', name: 'American Standards' },
      european: { flag: '🇪🇺', name: 'European Standards' },
      conservative: { flag: '👨‍👩‍👧‍👦', name: 'Conservative Standards' }
    };
    return info[standard as keyof typeof info] || { flag: '🌍', name: 'Global Standards' };
  };

  const standardInfo = getStandardInfo(culturalStandard);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Globe className="h-6 w-6 text-blue-400" />
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Cultural Content Processing
                </h2>
                <div className="flex items-center space-x-2 text-sm text-gray-400">
                  <span>{standardInfo.flag}</span>
                  <span>{standardInfo.name}</span>
                  {report && (
                    <span>• {report.total_scenes} scenes analyzed</span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {step === 'analyze' && (
            <div className="text-center py-8">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-medium text-white mb-2">
                Analyzing Content for Cultural Standards
              </h3>
              <p className="text-gray-400">
                Processing images locally with computer vision...
              </p>
            </div>
          )}

          {step === 'review' && report && (
            <div className="space-y-6">
              {/* Processing Summary */}
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="font-medium text-white mb-3">Analysis Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-400">{report.total_scenes}</div>
                    <div className="text-gray-400">Scenes Analyzed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-400">{report.modified_scenes}</div>
                    <div className="text-gray-400">Need Review</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{report.high_confidence_modifications}</div>
                    <div className="text-gray-400">High Confidence</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-400">
                      {Math.round(report.modification_rate)}%
                    </div>
                    <div className="text-gray-400">Modification Rate</div>
                  </div>
                </div>
              </div>

              {/* Scene Review Grid */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-white">Scene Modifications</h3>
                  <div className="text-sm text-gray-400">
                    {selectedScenes.size} of {results.filter(r => r.user_approval_required).length} selected
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
                  {results.map((result, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border cursor-pointer transition-all ${
                        result.user_approval_required
                          ? selectedScenes.has(index)
                            ? 'bg-blue-600 border-blue-500'
                            : 'bg-gray-800 border-gray-600 hover:bg-gray-700'
                          : 'bg-gray-900 border-gray-700 opacity-50'
                      }`}
                      onClick={() => result.user_approval_required && toggleSceneSelection(index)}
                    >
                      <div className="flex items-start space-x-3">
                        <div className="w-16 h-12 bg-gray-700 rounded flex items-center justify-center">
                          <Eye className="h-6 w-6 text-gray-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-white">Scene {index + 1}</span>
                            {result.user_approval_required && selectedScenes.has(index) && (
                              <Check className="h-4 w-4 text-blue-400" />
                            )}
                          </div>
                          <div className="text-sm text-gray-400 mb-2">{result.description}</div>
                          <div className="flex items-center space-x-2 text-xs">
                            <span className="bg-gray-700 px-2 py-1 rounded">
                              Confidence: {Math.round(result.confidence * 100)}%
                            </span>
                            {result.modifications_applied.map((mod, idx) => (
                              <span key={idx} className="bg-yellow-600 px-2 py-1 rounded">
                                {mod.replace('_', ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Privacy Notice */}
              <div className="bg-green-900/20 border border-green-700 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Shield className="h-5 w-5 text-green-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-400 mb-1">Privacy Protected</h4>
                    <p className="text-sm text-green-300">
                      All processing occurs locally on your machine. No images are uploaded or shared externally.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 'apply' && (
            <div className="text-center py-8">
              <div className="animate-spin w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-medium text-white mb-2">
                Applying Cultural Modifications
              </h3>
              <p className="text-gray-400">
                Processing {selectedScenes.size} scenes...
              </p>
            </div>
          )}

          {step === 'complete' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">
                Cultural Processing Complete
              </h3>
              <p className="text-gray-400 mb-4">
                {selectedScenes.size} scenes have been processed for {standardInfo.name}
              </p>
              <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 max-w-md mx-auto">
                <p className="text-sm text-blue-300">
                  Original images are preserved. You can regenerate the video with cultural modifications,
                  or revert to originals at any time.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-400">
            {step === 'review' && report && (
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-400" />
                <span>Review and approve modifications before applying</span>
              </div>
            )}
            {step === 'complete' && (
              <div className="flex items-center space-x-2">
                <Shield className="h-4 w-4 text-green-400" />
                <span>Processing complete, originals preserved</span>
              </div>
            )}
          </div>

          <div className="flex space-x-3">
            {step === 'review' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-300 hover:text-white border border-gray-600 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApproveSelected}
                  disabled={selectedScenes.size === 0 || processing}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Apply {selectedScenes.size} Modifications
                </button>
              </>
            )}
            {step === 'complete' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-300 hover:text-white border border-gray-600 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    onClose();
                    // Trigger video rebuild with modified scenes
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                  <Download className="h-4 w-4" />
                  <span>Rebuild Video</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CulturalProcessingModal;