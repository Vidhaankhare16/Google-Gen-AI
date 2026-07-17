import React, { useState, useCallback } from 'react';
import { Box, Typography, Button, LinearProgress, Chip } from '@mui/material';
import { CloudUpload, Description, Close, CheckCircle } from '@mui/icons-material';
import ApiService from '../services/api';
import { AnalysisResult } from '../types/api';

interface DocumentUploadProps {
  onUploadSuccess: (result: AnalysisResult) => void;
  onUploadError: (error: string) => void;
  isProcessing: boolean;
  setIsProcessing: (processing: boolean) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess, onUploadError, isProcessing, setIsProcessing,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileSelect = useCallback((file: File) => {
    const validation = ApiService.validateFile(file);
    if (!validation.isValid) { onUploadError(validation.error || 'Invalid file'); return; }
    setSelectedFile(file);
    onUploadError('');
  }, [onUploadError]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setDragOver(false); };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) handleFileSelect(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsProcessing(true); setUploadProgress(0);
    const interval = setInterval(() => setUploadProgress(p => p >= 82 ? 82 : p + 7), 350);
    try {
      const response = await ApiService.analyzeDocument(selectedFile);
      clearInterval(interval); setUploadProgress(100);
      if (response.success && response.analysis) onUploadSuccess(response.analysis);
      else throw new Error('Analysis failed');
    } catch (err: any) {
      clearInterval(interval);
      onUploadError(err.message || 'Failed to analyze document');
    } finally {
      setIsProcessing(false); setUploadProgress(0);
    }
  };

  const isActive = dragOver || (!!selectedFile && !isProcessing);

  return (
    <Box>
      <input id="file-input" type="file" accept=".pdf,application/pdf" onChange={handleFileInputChange} style={{ display: 'none' }} disabled={isProcessing} />

      {/* Drop zone with gradient border trick — bg color from theme */}
      <Box
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isProcessing && document.getElementById('file-input')?.click()}
        sx={(theme) => ({
          p: { xs: 5, md: 8 },
          textAlign: 'center',
          cursor: isProcessing ? 'default' : 'pointer',
          borderRadius: '20px',
          transition: 'all 0.3s ease',
          background: isActive
            ? `linear-gradient(${theme.palette.background.paper}, ${theme.palette.background.paper}) padding-box, linear-gradient(135deg, #7C3AED, #2563EB) border-box`
            : `linear-gradient(${theme.palette.background.paper}, ${theme.palette.background.paper}) padding-box, linear-gradient(135deg, rgba(124,58,237,0.35), rgba(37,99,235,0.35)) border-box`,
          border: '2px solid transparent',
          '&:hover': !isProcessing ? {
            background: `linear-gradient(${theme.palette.background.paper}, ${theme.palette.background.paper}) padding-box, linear-gradient(135deg, #7C3AED, #2563EB) border-box`,
            transform: 'translateY(-2px)',
            boxShadow: theme.palette.mode === 'dark'
              ? '0 16px 50px rgba(124,58,237,0.15)'
              : '0 16px 50px rgba(124,58,237,0.12)',
          } : {},
        })}
      >
        {/* Icon */}
        <Box sx={{
          width: 76, height: 76, borderRadius: '20px',
          background: dragOver ? 'linear-gradient(135deg, #7C3AED, #2563EB)' : 'rgba(124,58,237,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          mx: 'auto', mb: 3, transition: 'all 0.3s ease',
          boxShadow: dragOver ? '0 8px 30px rgba(124,58,237,0.4)' : 'none',
          ...(isProcessing && {
            '@keyframes uploadPulse': {
              '0%, 100%': { transform: 'scale(1)', opacity: 1 },
              '50%': { transform: 'scale(1.1)', opacity: 0.75 },
            },
            animation: 'uploadPulse 1.6s infinite ease-in-out',
          }),
        }}>
          <CloudUpload sx={{ fontSize: 38, color: dragOver ? 'white' : 'primary.main' }} />
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 700, mb: 1.5, color: 'text.primary' }}>
          {dragOver ? 'Drop your PDF here' : isProcessing ? 'Processing Document...' : 'Upload Legal Document'}
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
          {isProcessing
            ? 'Please wait while AI analyzes your document'
            : <span>Drag & drop or <Box component="span" sx={{ color: 'primary.main', textDecoration: 'underline' }}>click to browse</Box></span>
          }
        </Typography>

        {!isProcessing && (
          <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap' }}>
            {['PDF only', 'Max 10MB', 'Secure & Private'].map(tag => (
              <Chip key={tag} label={tag} size="small" sx={{ bgcolor: 'action.hover', color: 'text.secondary', fontSize: '0.75rem' }} />
            ))}
          </Box>
        )}
      </Box>

      {/* Selected file */}
      {selectedFile && !isProcessing && (
        <Box sx={(theme) => ({
          mt: 2, p: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(52,211,153,0.06)' : 'rgba(5,150,105,0.06)',
          border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(52,211,153,0.2)' : 'rgba(5,150,105,0.2)'}`,
          borderRadius: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          '@keyframes slideIn': { from: { opacity: 0, transform: 'translateY(-8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
          animation: 'slideIn 0.25s ease',
        })}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0 }}>
            <Box sx={{ width: 40, height: 40, borderRadius: '10px', flexShrink: 0, bgcolor: 'rgba(220,38,38,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Description sx={{ color: 'error.main', fontSize: 22 }} />
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedFile.name}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {ApiService.formatFileSize(selectedFile.size)} · Ready to analyze
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
            <CheckCircle sx={{ color: 'success.main', fontSize: 20 }} />
            <Close sx={{ color: 'text.secondary', cursor: 'pointer', fontSize: 20, '&:hover': { color: 'text.primary' } }} onClick={e => { e.stopPropagation(); setSelectedFile(null); }} />
          </Box>
        </Box>
      )}

      {/* Progress */}
      {isProcessing && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 500 }}>
              {uploadProgress < 80 ? '📤 Uploading document...' : '🤖 Analyzing with AI...'}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 600 }}>{uploadProgress}%</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={uploadProgress}
            sx={{ height: 6, borderRadius: 3, bgcolor: 'action.disabledBackground', '& .MuiLinearProgress-bar': { borderRadius: 3, background: 'linear-gradient(90deg, #7C3AED, #2563EB)' } }}
          />
          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 1, display: 'block' }}>
            This may take up to 30 seconds for complex documents
          </Typography>
        </Box>
      )}

      {/* Analyze button */}
      {!isProcessing && (
        <Button variant="contained" fullWidth onClick={handleUpload} disabled={!selectedFile} size="large" endIcon={<CloudUpload />} sx={{ mt: 3, py: 1.75, fontSize: '1rem' }}>
          {selectedFile ? 'Analyze Document' : 'Select a PDF to get started'}
        </Button>
      )}

      {!isProcessing && !selectedFile && (
        <Typography variant="caption" sx={{ display: 'block', textAlign: 'center', color: 'text.secondary', mt: 2, opacity: 0.7 }}>
          Documents are processed securely and stored temporarily. No data is retained after your session.
        </Typography>
      )}
    </Box>
  );
};

export default DocumentUpload;
