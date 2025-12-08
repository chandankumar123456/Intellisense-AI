import React from 'react';
import { FileText, Upload } from 'lucide-react';
import Button from '../../common/Button';

const MyFilesTab: React.FC = () => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text_primary">My Files</h3>
        <Button variant="secondary" size="sm">
          <Upload className="w-4 h-4 mr-2" />
          Upload
        </Button>
      </div>
      <div className="text-center py-8 text-text_secondary">
        <FileText className="w-12 h-12 mx-auto mb-4 text-text_secondary/50" />
        <p>No files uploaded yet</p>
        <p className="text-sm mt-2">Upload documents to search through them</p>
      </div>
    </div>
  );
};

export default MyFilesTab;
