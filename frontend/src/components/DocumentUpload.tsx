import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, Typography, Button } from '@mui/material';
import ApiService from '../services/api';
import { AnalysisResult } from '../types/api';
import { Eyebrow } from './Annotation';
import { MONO, DISPLAY } from '../theme';

interface DocumentUploadProps {
  onUploadSuccess: (result: AnalysisResult, filename: string) => void;
  onUploadError: (error: string) => void;
  isProcessing: boolean;
  setIsProcessing: (processing: boolean) => void;
}

/**
 * The four steps the backend actually runs, in order. They advance on an estimated
 * schedule — the API returns one response rather than streaming — so this is a map of
 * where the work is, not a measured percentage.
 */
const STEPS = [
  'Reading the PDF',
  'Indexing the clauses',
  'Retrieving Indian law',
  'Writing the findings',
];

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadSuccess, onUploadError, isProcessing, setIsProcessing }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [step, setStep] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isProcessing) { setStep(0); return; }
    // Hold on the last step rather than looping — the work really is still in that phase.
    const id = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 4200);
    return () => clearInterval(id);
  }, [isProcessing]);

  const handleFileSelect = useCallback((file: File) => {
    const validation = ApiService.validateFile(file);
    if (!validation.isValid) { onUploadError(validation.error || 'That file could not be read.'); return; }
    setSelectedFile(file);
    onUploadError('');
  }, [onUploadError]);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    try {
      const response = await ApiService.analyzeDocument(selectedFile);
      if (response.success && response.analysis) onUploadSuccess(response.analysis, selectedFile.name);
      else throw new Error('The document was read but no analysis came back. Try again.');
    } catch (err: any) {
      onUploadError(err.message || 'The document could not be analysed. Try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const openPicker = () => { if (!isProcessing) inputRef.current?.click(); };

  return (
    <Box>
      <input
        ref={inputRef}
        id="file-input"
        type="file"
        accept=".pdf,application/pdf"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); e.target.value = ''; }}
        style={{ display: 'none' }}
        disabled={isProcessing}
      />

      {/* Drop zone — ruled like the stamp paper the contract was printed on. */}
      <Box
        role="button"
        tabIndex={isProcessing ? -1 : 0}
        aria-label="Choose a PDF to read"
        onClick={openPicker}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPicker(); } }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragOver(false); }}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) handleFileSelect(e.dataTransfer.files[0]); }}
        sx={(t) => ({
          position: 'relative',
          px: { xs: 3, md: 6 }, py: { xs: 5, md: 7 },
          borderRadius: 2,
          cursor: isProcessing ? 'default' : 'pointer',
          border: `1px ${dragOver ? 'solid' : 'dashed'} ${dragOver || selectedFile ? t.palette.primary.main : t.palette.divider}`,
          bgcolor: 'background.paper',
          transition: 'border-color .18s, background-color .18s',
          // Faint horizontal ruling, like lined legal paper.
          backgroundImage: `repeating-linear-gradient(to bottom, transparent, transparent 27px, ${t.palette.divider} 27px, ${t.palette.divider} 28px)`,
          backgroundPosition: '0 6px',
          '&:hover': isProcessing ? {} : { borderColor: t.palette.primary.main },
          '&:focus-visible': { outline: `2px solid ${t.palette.primary.main}`, outlineOffset: 3 },
        })}
      >
        {!isProcessing ? (
          <Box sx={{ textAlign: 'center' }}>
            <Eyebrow sx={{ color: 'primary.main' }}>{dragOver ? 'Let go' : 'Step one'}</Eyebrow>
            <Typography sx={{ fontFamily: DISPLAY, fontSize: { xs: '1.6rem', md: '2rem' }, mt: 1.5, lineHeight: 1.2 }}>
              {dragOver ? 'Drop the contract here' : 'Drop a contract, or choose a file'}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1.5 }}>
              PDF, up to 10&nbsp;MB. Scanned pages are read too.
            </Typography>
          </Box>
        ) : (
          <Box sx={{ maxWidth: 420, mx: 'auto' }}>
            <Eyebrow sx={{ color: 'primary.main', textAlign: 'center' }}>Reading</Eyebrow>
            <Box sx={{ mt: 2.5, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
              {STEPS.map((label, i) => {
                const state = i < step ? 'done' : i === step ? 'active' : 'todo';
                return (
                  <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 1.75 }}>
                    <Typography sx={{ fontFamily: MONO, fontSize: '0.7rem', color: state === 'todo' ? 'text.secondary' : 'primary.main', opacity: state === 'todo' ? 0.5 : 1, width: 20 }}>
                      {state === 'done' ? '✓' : String(i + 1).padStart(2, '0')}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        color: state === 'todo' ? 'text.secondary' : 'text.primary',
                        opacity: state === 'todo' ? 0.5 : 1,
                        '@keyframes breathe': { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.45 } },
                        animation: state === 'active' ? 'breathe 1.8s ease-in-out infinite' : 'none',
                      }}
                    >
                      {label}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
            <Typography variant="caption" sx={{ display: 'block', textAlign: 'center', color: 'text.secondary', mt: 3 }}>
              About half a minute — longer if the service is waking up.
            </Typography>
          </Box>
        )}
      </Box>

      {/* Selected file */}
      {selectedFile && !isProcessing && (
        <Box
          sx={(t) => ({
            mt: 2, px: 2.5, py: 1.75, borderRadius: 1.5,
            border: `1px solid ${t.palette.divider}`, borderLeft: `3px solid ${t.palette.secondary.main}`,
            bgcolor: 'background.paper',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2,
          })}
        >
          <Box sx={{ minWidth: 0 }}>
            <Eyebrow sx={{ color: 'secondary.main' }}>Ready</Eyebrow>
            <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.25, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedFile.name}
            </Typography>
            <Typography sx={{ fontFamily: MONO, fontSize: '0.68rem', color: 'text.secondary', mt: 0.25 }}>
              {ApiService.formatFileSize(selectedFile.size)}
            </Typography>
          </Box>
          <Button size="small" onClick={() => setSelectedFile(null)} sx={{ color: 'text.secondary', flexShrink: 0 }}>
            Remove
          </Button>
        </Box>
      )}

      {!isProcessing && (
        <Button variant="contained" fullWidth size="large" onClick={handleUpload} disabled={!selectedFile} sx={{ mt: 2, py: 1.5 }}>
          {selectedFile ? 'Read this contract' : 'Choose a PDF first'}
        </Button>
      )}

      <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 2, textAlign: 'center' }}>
        Your file stays in memory for the session and is deleted when it ends.
      </Typography>
    </Box>
  );
};

export default DocumentUpload;
