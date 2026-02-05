import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Music, X, FileAudio } from 'lucide-react';

interface AudioUploadProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
}

const AudioUpload: React.FC<AudioUploadProps> = ({ onFileSelect, selectedFile }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.flac', '.ogg']
    },
    multiple: false,
    maxSize: 100 * 1024 * 1024 // 100MB
  });

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (selectedFile) {
    return (
      <div className="border-2 border-dashed border-green-500 rounded-lg p-6 bg-green-900/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <FileAudio className="h-6 w-6 text-green-400" />
            </div>
            <div>
              <p className="font-medium text-white">{selectedFile.name}</p>
              <p className="text-sm text-dark-300">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            onClick={handleRemove}
            className="p-2 text-dark-400 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${
        isDragActive
          ? 'border-primary-400 bg-primary-900/20'
          : 'border-dark-500 hover:border-dark-400 bg-dark-800/50'
      }`}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center space-y-4">
        <div className={`p-4 rounded-full ${isDragActive ? 'bg-primary-500/20' : 'bg-dark-600'}`}>
          {isDragActive ? (
            <Upload className="h-8 w-8 text-primary-400" />
          ) : (
            <Music className="h-8 w-8 text-dark-400" />
          )}
        </div>

        <div>
          <p className="text-lg font-medium text-white">
            {isDragActive ? 'Drop your audio file here' : 'Upload your music'}
          </p>
          <p className="text-sm text-dark-400 mt-1">
            Drag & drop or click to select • MP3, WAV, M4A, FLAC
          </p>
          <p className="text-xs text-dark-500 mt-1">
            Maximum file size: 100MB
          </p>
        </div>
      </div>
    </div>
  );
};

export default AudioUpload;