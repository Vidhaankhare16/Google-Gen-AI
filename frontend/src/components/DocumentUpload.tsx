import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  Alert,
  Paper,
  IconButton,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as PdfIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

import ApiService from '../services/api';
import { AnalysisResult } from '../types/api';

const UploadArea = styled(Paper)(({ theme }) => ({
  border: `2px dashed #d0d7de`,
  borderRadius: theme.spacing(2),
  padding: theme.spacing(8, 4),
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  backgroundColor: '#fafbfc',
  '&:hover': {
    borderColor: '#1976d2',
    backgroundColor: '#f6f8fa',
    transform: 'translateY(-1px)',
  },
  '&.drag-over': {
    borderColor: '#1976d2',
    backgroundColor: '#e3f2fd',
    borderStyle: 'solid',
  },
}));

const FileInfo = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.spacing(1),
  marginTop: theme.spacing(2),
}));

interface DocumentUploadProps {
  onUploadSuccess: (result: AnalysisResult) => void;
  onUploadError: (error: string) => void;
  isProcessing: boolean;
  setIsProcessing: (processing: boolean) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
  onUploadError,
  isProcessing,
  setIsProcessing,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileSelect = useCallback((file: File) => {
    // Validate file
    const validation = ApiService.validateFile(file);
    if (!validation.isValid) {
      onUploadError(validation.error || 'Invalid file');
      return;
    }

    setSelectedFile(file);
    onUploadError(''); // Clear any previous errors
  }, [onUploadError]);

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      onUploadError('Please select a file first');
      return;
    }

    setIsProcessing(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const response = await ApiService.analyzeDocument(selectedFile);

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.success && response.analysis) {
        onUploadSuccess(response.analysis);
      } else {
        throw new Error('Analysis failed');
      }
    } catch (error: any) {
      onUploadError(error.message || 'Failed to analyze document');
    } finally {
      setIsProcessing(false);
      setUploadProgress(0);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    onUploadError('');
  };

  const handleAreaClick = () => {
    if (!isProcessing) {
      document.getElementById('file-input')?.click();
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Upload Legal Document
      </Typography>

      <input
        id="file-input"
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
        disabled={isProcessing}
      />

      <UploadArea
        className={dragOver ? 'drag-over' : ''}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleAreaClick}
      >
        <UploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 3 }} />
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
          {dragOver ? 'Drop your PDF here' : 'Upload Your Legal Document'}
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
          Drag & drop your PDF here or click to browse
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.7 }}>
          Maximum file size: 10MB • PDF files only
        </Typography>
      </UploadArea>

      {selectedFile && (
        <FileInfo>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <PdfIcon sx={{ mr: 1, color: 'error.main' }} />
            <Box>
              <Typography variant="body2" fontWeight="medium">
                {selectedFile.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {ApiService.formatFileSize(selectedFile.size)}
              </Typography>
            </Box>
          </Box>
          <IconButton
            size="small"
            onClick={handleRemoveFile}
            disabled={isProcessing}
          >
            <CloseIcon />
          </IconButton>
        </FileInfo>
      )}

      {isProcessing && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" gutterBottom>
            Analyzing document... This may take a few moments.
          </Typography>
          <LinearProgress
            variant="determinate"
            value={uploadProgress}
            sx={{ mb: 1 }}
          />
          <Typography variant="caption" color="text.secondary">
            {uploadProgress < 90 ? 'Uploading...' : 'Processing with AI...'}
          </Typography>
        </Box>
      )}

      <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={!selectedFile || isProcessing}
          startIcon={<UploadIcon />}
          fullWidth
        >
          {isProcessing ? 'Analyzing...' : 'Analyze Document'}
        </Button>
      </Box>

      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="body2">
          Your document will be processed securely and can be deleted after analysis. 
          We support PDF files up to 10MB in size.
        </Typography>
      </Alert>
    </Box>
  );
};

export default DocumentUpload;