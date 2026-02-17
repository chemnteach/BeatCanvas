import React, { useRef } from 'react';
import { Upload, X, Image as ImageIcon, User, Mountain } from 'lucide-react';

interface ReferenceImageUploadProps {
  type: 'character' | 'background';
  images: File[];
  descriptions: string[];
  onImageAdd: (files: FileList | null) => void;
  onImageRemove: (index: number) => void;
  onDescriptionUpdate: (index: number, description: string) => void;
}

const ReferenceImageUpload: React.FC<ReferenceImageUploadProps> = ({
  type,
  images,
  descriptions,
  onImageAdd,
  onImageRemove,
  onDescriptionUpdate
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    onImageAdd(e.target.files);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    onImageAdd(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const getTypeIcon = () => {
    return type === 'character' ? <User className="h-5 w-5" /> : <Mountain className="h-5 w-5" />;
  };

  const getTypeTitle = () => {
    return type === 'character' ? 'Character References' : 'Background References';
  };

  const getTypeDescription = () => {
    return type === 'character'
      ? 'Upload images of characters you want to appear in the video'
      : 'Upload images of backgrounds, environments, or visual styles you want';
  };

  return (
    <div className="bg-dark-700 rounded-xl p-6 border border-dark-600">
      <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
        {getTypeIcon()}
        <span className="ml-2">{getTypeTitle()}</span>
      </h3>
      <p className="text-dark-300 text-sm mb-4">{getTypeDescription()}</p>

      {/* Upload Area */}
      <div
        className="border-2 border-dashed border-dark-500 rounded-lg p-6 text-center cursor-pointer hover:border-primary-500 transition-colors"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload className="h-8 w-8 text-dark-400 mx-auto mb-2" />
        <p className="text-dark-300 mb-1">Drop images here or click to browse</p>
        <p className="text-dark-400 text-xs">PNG, JPG up to 10MB each</p>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Uploaded Images */}
      {images.length > 0 && (
        <div className="mt-4 space-y-3">
          <h4 className="text-white font-medium">Uploaded References</h4>
          {images.map((image, index) => (
            <div key={index} className="bg-dark-800 rounded-lg p-4 flex items-start space-x-4">
              {/* Image Preview */}
              <div className="w-16 h-16 bg-dark-600 rounded-lg flex items-center justify-center overflow-hidden flex-shrink-0">
                <img
                  src={URL.createObjectURL(image)}
                  alt={`Reference ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              </div>

              {/* Image Info and Description */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-white text-sm font-medium">{image.name}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onImageRemove(index);
                    }}
                    className="text-red-400 hover:text-red-300 p-1"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <textarea
                  placeholder={`Describe this ${type}...`}
                  value={descriptions[index] || ''}
                  onChange={(e) => onDescriptionUpdate(index, e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-md px-3 py-2 text-white text-sm placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  rows={2}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReferenceImageUpload;