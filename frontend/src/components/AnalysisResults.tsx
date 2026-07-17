import React, { useState } from 'react';
import { Box, Typography, Button, Chip, Collapse, IconButton } from '@mui/material';
import { ExpandMore, ExpandLess, Refresh } from '@mui/icons-material';
import { AnalysisResult } from '../types/api';
import ApiService from '../services/api';

interface AnalysisResultsProps {
  result: AnalysisResult;
  onNewDocument: () => void;
}

const RiskGauge: React.FC<{ score: number }> = ({ score }) => {
  const s = Math.min(Math.max(score, 0), 10);
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const progress = (s / 10) * circumference;
  const color = s >= 7 ? '#F87171' : s >= 4 ? '#FBBF24' : '#34D399';
  const label = s >= 7 ? 'HIGH RISK' : s >= 4 ? 'MEDIUM RISK' : 'LOW RISK';
  const glow = s >= 7 ? 'rgba(248,113,113,0.25)' : s >= 4 ? 'rgba(251,191,36,0.25)' : 'rgba(52,211,153,0.25)';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.75, flexShrink: 0 }}>
      <svg width="120" height="120" viewBox="0 0 120 120" style={{ filter: `drop-shadow(0 0 14px ${glow})` }}>
        <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(128,128,128,0.15)" strokeWidth="10" />
        <circle cx="60" cy="60" r={radius} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`} transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dasharray 1.3s cubic-bezier(0.4,0,0.2,1)' }} />
        <text x="60" y="55" textAnchor="middle" fill={color} fontSize="30" fontWeight="800" fontFamily="Inter, sans-serif">{s}</text>
        <text x="60" y="73" textAnchor="middle" fill="gray" fontSize="12" fontFamily="Inter, sans-serif">/ 10</text>
      </svg>
      <Typography sx={{ color, fontWeight: 800, fontSize: '0.65rem', letterSpacing: '0.1em' }}>{label}</Typography>
    </Box>
  );
};

type Severity = 'high' | 'medium' | 'low';

const getSeverity = (w: string): Severity => {
  const u = w.toUpperCase();
  if (u.startsWith('[HIGH]')) return 'high';
  if (u.startsWith('[MEDIUM]')) return 'medium';
  return 'low';
};

const getWarningText = (w: string) => w.replace(/^\[(HIGH|MEDIUM|LOW)\]\s*/i, '');

const SEV = {
  high:   { bg: 'rgba(220,38,38,0.07)',   border: 'rgba(220,38,38,0.2)',   dot: '#F87171', label: 'HIGH' },
  medium: { bg: 'rgba(217,119,6,0.07)',   border: 'rgba(217,119,6,0.2)',   dot: '#FBBF24', label: 'MED' },
  low:    { bg: 'rgba(5,150,105,0.06)',   border: 'rgba(5,150,105,0.18)',  dot: '#34D399', label: 'LOW' },
};

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ result, onNewDocument }) => {
  const [showKeyPoints, setShowKeyPoints] = useState(true);
  const [showWarnings, setShowWarnings] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try { await ApiService.deleteDocument(result.document_id); } catch {}
    setIsDeleting(false);
    onNewDocument();
  };

  const riskScore = typeof result.risk_score === 'number' ? result.risk_score : 5;
  const documentType = result.document_type ?? 'Legal Document';
  const keyPoints = result.key_points ?? [];
  const warnings = result.warnings ?? [];

  return (
    <Box sx={{ '@keyframes fadeInUp': { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } }, animation: 'fadeInUp 0.4s ease forwards' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Chip label={documentType} size="small" sx={{ background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.3)', color: 'primary.main', fontWeight: 600, mb: 1 }} />
          <Typography variant="h4">Analysis Results</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" variant="outlined" onClick={handleDelete} disabled={isDeleting}
            sx={{ borderColor: 'rgba(220,38,38,0.35)', color: 'error.main', '&:hover': { borderColor: 'error.main', bgcolor: 'rgba(220,38,38,0.06)' }, fontSize: '0.8rem' }}>
            {isDeleting ? 'Deleting...' : 'Delete'}
          </Button>
          <Button size="small" variant="outlined" startIcon={<Refresh sx={{ fontSize: '16px !important' }} />} onClick={onNewDocument}
            sx={{ borderColor: 'divider', color: 'text.secondary', '&:hover': { color: 'text.primary' }, fontSize: '0.8rem' }}>
            New Document
          </Button>
        </Box>
      </Box>

      {/* Summary card with gauge */}
      <Box sx={(theme) => ({
        p: 3, mb: 3, borderRadius: '20px',
        background: theme.palette.mode === 'dark'
          ? 'linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(37,99,235,0.06) 100%)'
          : 'linear-gradient(135deg, rgba(124,58,237,0.06) 0%, rgba(37,99,235,0.03) 100%)',
        border: '1px solid rgba(124,58,237,0.2)',
        display: 'flex', gap: { xs: 2, sm: 3 },
        flexDirection: { xs: 'column', sm: 'row' },
        alignItems: { xs: 'center', sm: 'flex-start' },
      })}>
        <RiskGauge score={riskScore} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h5" sx={{ mb: 1.5 }}>Summary</Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>{result.summary || 'No summary available.'}</Typography>
        </Box>
      </Box>

      {/* Key Points */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, cursor: 'pointer', userSelect: 'none' }} onClick={() => setShowKeyPoints(v => !v)}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ width: 4, height: 22, borderRadius: 2, bgcolor: 'success.main', flexShrink: 0 }} />
            <Typography variant="h5">Key Points</Typography>
            <Chip label={keyPoints.length} size="small" sx={{ bgcolor: 'rgba(5,150,105,0.1)', color: 'success.main', fontWeight: 700, height: 22, fontSize: '0.75rem' }} />
          </Box>
          <IconButton size="small" sx={{ color: 'text.secondary' }}>{showKeyPoints ? <ExpandLess /> : <ExpandMore />}</IconButton>
        </Box>

        <Collapse in={showKeyPoints}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {keyPoints.length > 0 ? keyPoints.map((point, i) => (
              <Box key={i} sx={(theme) => ({
                p: 2, borderRadius: '12px',
                bgcolor: theme.palette.mode === 'dark' ? 'rgba(52,211,153,0.04)' : 'rgba(5,150,105,0.04)',
                border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(52,211,153,0.12)' : 'rgba(5,150,105,0.15)'}`,
                borderLeft: '3px solid', borderLeftColor: 'success.main',
                display: 'flex', gap: 2,
                '@keyframes fadeIn': { from: { opacity: 0 }, to: { opacity: 1 } },
                animation: `fadeIn 0.3s ${i * 0.06}s ease forwards`, opacity: 0,
              })}>
                <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 800, bgcolor: 'rgba(5,150,105,0.1)', px: 1, py: 0.3, borderRadius: '6px', alignSelf: 'flex-start', flexShrink: 0, fontSize: '0.72rem', mt: 0.25, minWidth: '28px', textAlign: 'center' }}>
                  {String(i + 1).padStart(2, '0')}
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.7, pt: 0.2 }}>{point}</Typography>
              </Box>
            )) : (
              <Typography variant="body2" sx={{ color: 'text.secondary', p: 2 }}>No key points identified.</Typography>
            )}
          </Box>
        </Collapse>
      </Box>

      {/* Warnings */}
      {warnings.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, cursor: 'pointer', userSelect: 'none' }} onClick={() => setShowWarnings(v => !v)}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ width: 4, height: 22, borderRadius: 2, bgcolor: 'error.main', flexShrink: 0 }} />
              <Typography variant="h5">Warnings</Typography>
              <Chip label={warnings.length} size="small" sx={{ bgcolor: 'rgba(220,38,38,0.1)', color: 'error.main', fontWeight: 700, height: 22, fontSize: '0.75rem' }} />
            </Box>
            <IconButton size="small" sx={{ color: 'text.secondary' }}>{showWarnings ? <ExpandLess /> : <ExpandMore />}</IconButton>
          </Box>

          <Collapse in={showWarnings}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {warnings.map((warning, i) => {
                const sev = getSeverity(warning);
                const cfg = SEV[sev];
                return (
                  <Box key={i} sx={{
                    p: 2, borderRadius: '12px',
                    bgcolor: cfg.bg, border: `1px solid ${cfg.border}`, borderLeft: `3px solid ${cfg.dot}`,
                    display: 'flex', gap: 2, alignItems: 'flex-start',
                    '@keyframes fadeIn': { from: { opacity: 0 }, to: { opacity: 1 } },
                    animation: `fadeIn 0.3s ${i * 0.06}s ease forwards`, opacity: 0,
                  }}>
                    <Chip label={cfg.label} size="small" sx={{ bgcolor: cfg.bg, color: cfg.dot, border: `1px solid ${cfg.border}`, fontWeight: 800, fontSize: '0.65rem', height: 22, flexShrink: 0 }} />
                    <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.7, pt: 0.2 }}>{getWarningText(warning)}</Typography>
                  </Box>
                );
              })}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Disclaimer */}
      <Box sx={(theme) => ({
        mt: 2, p: 2, borderRadius: '12px',
        bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
        border: `1px solid ${theme.palette.divider}`,
      })}>
        <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.7, display: 'block' }}>
          ⚠️ <strong>Disclaimer:</strong> This analysis is for informational purposes only and does not constitute legal advice. Always consult with a qualified attorney for legal matters.
        </Typography>
      </Box>
    </Box>
  );
};

export default AnalysisResults;
