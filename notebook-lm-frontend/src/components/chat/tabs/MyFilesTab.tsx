import React, { useRef } from 'react';
import { FileText, Upload, X } from 'lucide-react';
import Button from '../../common/Button';
import { useChat } from '../../../contexts/ChatContext';

const MyFilesTab: React.FC = () => {
  const { files, addFile, removeFile } = useChat();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await addFile(file);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text_primary">My Files</h3>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.txt,.md,.doc,.docx"
        />
        <Button variant="secondary" size="sm" onClick={handleUploadClick}>
          <Upload className="w-4 h-4 mr-2" />
          Upload
        </Button>
      </div>

      {files.length === 0 ? (
        <div className="text-center py-8 text-text_secondary">
          <FileText className="w-12 h-12 mx-auto mb-4 text-text_secondary/50" />
          <p>No files uploaded yet</p>
          <p className="text-sm mt-2">Upload documents to search through them</p>
        </div>
      ) : (
        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-surface rounded-lg border border-border group"
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <FileText className="w-5 h-5 text-primary flex-shrink-0" />
                <div className="truncate">
                  <p className="text-sm font-medium text-text_primary truncate">{file.name}</p>
                  <p className="text-xs text-text_secondary">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={() => removeFile(file.id)}
                className="p-1 text-text_secondary hover:text-error opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyFilesTab;
