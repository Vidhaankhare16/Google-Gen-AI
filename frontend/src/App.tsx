import React, { useState, useMemo } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  GlobalStyles,
  Box,
  Container,
  Typography,
  Button,
  AppBar,
  Toolbar,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import { AutoAwesome, ArrowForward, Gavel, DarkMode, LightMode } from '@mui/icons-material';
import DocumentUpload from './components/DocumentUpload';
import AnalysisResults from './components/AnalysisResults';
import QAInterface from './components/QAInterface';
import { AnalysisResult } from './types/api';

const buildTheme = (mode: 'dark' | 'light') =>
  createTheme({
    palette: {
      mode,
      primary: {
        main: '#7C3AED',
        light: '#A78BFA',
        dark: '#5B21B6',
      },
      secondary: {
        main: '#2563EB',
        light: '#60A5FA',
        dark: '#1D4ED8',
      },
      background: {
        default: mode === 'dark' ? '#0B0B18' : '#F7F4FF',
        paper:   mode === 'dark' ? '#141428' : '#FFFFFF',
      },
      text: {
        primary:   mode === 'dark' ? '#F1F5F9' : '#1E1B4B',
        secondary: mode === 'dark' ? '#94A3B8' : '#64748B',
      },
      error:   { main: mode === 'dark' ? '#F87171' : '#DC2626', light: '#FCA5A5' },
      warning: { main: mode === 'dark' ? '#FBBF24' : '#D97706', light: '#FDE68A' },
      success: { main: mode === 'dark' ? '#34D399' : '#059669', light: '#A7F3D0' },
      divider: mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontSize: 'clamp(2.25rem, 5vw, 3.75rem)', fontWeight: 800, lineHeight: 1.1, letterSpacing: '-0.02em' },
      h2: { fontSize: '2.25rem', fontWeight: 700, lineHeight: 1.2 },
      h3: { fontSize: '1.5rem', fontWeight: 700 },
      h4: { fontSize: '1.25rem', fontWeight: 700 },
      h5: { fontSize: '1.05rem', fontWeight: 600 },
      h6: { fontSize: '0.95rem', fontWeight: 600 },
      body1: { fontSize: '1rem', lineHeight: 1.75 },
      body2: { fontSize: '0.875rem', lineHeight: 1.6 },
    },
    shape: { borderRadius: 16 },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { textTransform: 'none', fontWeight: 600, borderRadius: 12, fontSize: '0.95rem', transition: 'all 0.2s ease' },
          containedPrimary: {
            background: 'linear-gradient(135deg, #7C3AED 0%, #2563EB 100%)',
            color: '#FFFFFF',
            '&:hover': { background: 'linear-gradient(135deg, #6D28D9 0%, #1D4ED8 100%)', transform: 'translateY(-1px)', boxShadow: '0 8px 25px rgba(124,58,237,0.35)' },
            '&.Mui-disabled': { background: 'linear-gradient(135deg, #7C3AED 0%, #2563EB 100%)', opacity: 0.4, color: '#FFFFFF' },
          },
        },
      },
      MuiChip: {
        styleOverrides: { root: { borderRadius: 8, fontWeight: 500 } },
      },
      MuiPaper: {
        styleOverrides: {
          root: ({ theme }: any) => ({
            backgroundImage: 'none',
            border: `1px solid ${theme.palette.divider}`,
          }),
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: ({ theme }: any) => ({
            backgroundImage: 'none',
            backgroundColor: theme.palette.mode === 'dark' ? 'rgba(11,11,24,0.85)' : 'rgba(247,244,255,0.85)',
            backdropFilter: 'blur(20px)',
            borderBottom: `1px solid ${theme.palette.divider}`,
            boxShadow: 'none',
          }),
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: ({ theme }: any) => ({
            '& .MuiOutlinedInput-root': {
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
              '& fieldset': { borderColor: theme.palette.divider },
              '&:hover fieldset': { borderColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)' },
              '&.Mui-focused fieldset': { borderColor: '#7C3AED' },
            },
          }),
        },
      },
      MuiIconButton: {
        styleOverrides: { root: { borderRadius: 10 } },
      },
    },
  });

function App() {
  const [mode, setMode] = useState<'dark' | 'light'>('dark');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const theme = useMemo(() => buildTheme(mode), [mode]);

  const globalStyles = useMemo(() => ({
    '*': { boxSizing: 'border-box' },
    html: { scrollBehavior: 'smooth' },
    body: { backgroundColor: mode === 'dark' ? '#0B0B18' : '#F7F4FF', margin: 0, fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif' },
    '::-webkit-scrollbar': { width: '5px', height: '5px' },
    '::-webkit-scrollbar-track': { background: mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.03)' },
    '::-webkit-scrollbar-thumb': { background: 'rgba(124,58,237,0.3)', borderRadius: '3px', '&:hover': { background: 'rgba(124,58,237,0.5)' } },
  }), [mode]);

  const handleUploadSuccess = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleUploadError = (errorMessage: string) => {
    if (errorMessage) setError(errorMessage);
    setAnalysisResult(null);
  };

  const handleNewDocument = () => { setAnalysisResult(null); setError(null); };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <GlobalStyles styles={globalStyles} />

      {/* Navbar */}
      <AppBar position="fixed" elevation={0}>
        <Toolbar sx={{ justifyContent: 'space-between', py: 1, px: { xs: 2, md: 4 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 36, height: 36,
              background: 'linear-gradient(135deg, #7C3AED, #2563EB)',
              borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(124,58,237,0.35)',
            }}>
              <Gavel sx={{ color: 'white', fontSize: 20 }} />
            </Box>
            <Typography variant="h6" sx={{
              background: 'linear-gradient(135deg, #A78BFA 0%, #60A5FA 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              fontWeight: 800,
              letterSpacing: '-0.01em',
            }}>
              Legal EASE
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
            {!analysisResult && (
              <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 3, mr: 1 }}>
                {['Features', 'How it Works'].map(item => (
                  <Typography key={item} variant="body2" sx={{ color: 'text.secondary', cursor: 'pointer', '&:hover': { color: 'text.primary' }, transition: 'color 0.2s' }}>
                    {item}
                  </Typography>
                ))}
              </Box>
            )}

            {/* Light/Dark toggle */}
            <Tooltip title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
              <IconButton
                size="small"
                onClick={() => setMode(m => m === 'dark' ? 'light' : 'dark')}
                sx={{
                  color: 'text.secondary',
                  bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
                  '&:hover': { bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)', color: 'text.primary' },
                  width: 34, height: 34,
                }}
              >
                {mode === 'dark' ? <LightMode sx={{ fontSize: 18 }} /> : <DarkMode sx={{ fontSize: 18 }} />}
              </IconButton>
            </Tooltip>

            {analysisResult ? (
              <Button
                variant="outlined"
                size="small"
                onClick={handleNewDocument}
                sx={{
                  borderColor: 'rgba(124,58,237,0.35)',
                  color: 'primary.light',
                  '&:hover': { borderColor: 'primary.main', bgcolor: 'rgba(124,58,237,0.08)' },
                }}
              >
                ← New Document
              </Button>
            ) : (
              <Button
                variant="contained"
                size="small"
                onClick={() => document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Get Started
              </Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <Box sx={{ pt: '64px', minHeight: '100vh', bgcolor: 'background.default' }}>
        {!analysisResult ? (
          <Box>
            {/* Hero */}
            <Box sx={{ position: 'relative', overflow: 'hidden', pt: { xs: 8, md: 12 }, pb: { xs: 6, md: 8 }, textAlign: 'center' }}>
              <Box sx={{ position: 'absolute', top: '-15%', left: '-8%', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(60px)', pointerEvents: 'none' }} />
              <Box sx={{ position: 'absolute', top: '-5%', right: '-5%', width: '500px', height: '500px', background: 'radial-gradient(circle, rgba(37,99,235,0.1) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(60px)', pointerEvents: 'none' }} />

              <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
                <Chip
                  icon={<AutoAwesome sx={{ fontSize: '13px !important', color: '#A78BFA !important' }} />}
                  label="AI-Powered Legal Analysis"
                  size="small"
                  sx={{ mb: 4, background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.3)', color: 'primary.main', px: 1 }}
                />

                <Typography variant="h1" sx={{ mb: 3 }}>
                  Demystify{' '}
                  <Box component="span" sx={{ background: 'linear-gradient(135deg, #A78BFA 0%, #60A5FA 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                    Legal Documents
                  </Box>
                  {' '}with AI
                </Typography>

                <Typography variant="body1" sx={{ color: 'text.secondary', mb: 5, maxWidth: 560, mx: 'auto', fontSize: '1.1rem' }}>
                  Transform dense legal jargon into clear, actionable insights.
                  Understand contracts, NDAs, and agreements before you sign.
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap', mb: 5 }}>
                  <Button variant="contained" size="large" endIcon={<ArrowForward />} onClick={() => document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth' })} sx={{ px: 4, py: 1.5 }}>
                    Analyze a Document
                  </Button>
                  <Button
                    variant="outlined" size="large"
                    onClick={() => window.open('https://wa.me/14155238886?text=join%20legal-ease-demo', '_blank')}
                    sx={{ px: 4, py: 1.5, borderColor: 'rgba(37,99,235,0.4)', color: 'secondary.main', '&:hover': { borderColor: 'secondary.main', bgcolor: 'rgba(37,99,235,0.06)' } }}
                  >
                    📱 WhatsApp Demo
                  </Button>
                </Box>

                <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap' }}>
                  {['⚡ Instant Analysis', '🔒 Privacy First', '📊 Risk Scoring', '💬 Ask Questions', '🎯 Plain English'].map(f => (
                    <Chip key={f} label={f} size="small" variant="outlined" sx={{ borderColor: 'divider', color: 'text.secondary', '&:hover': { borderColor: 'text.secondary' } }} />
                  ))}
                </Box>
              </Container>
            </Box>

            {/* Upload */}
            <Container maxWidth="md" id="upload-section" sx={{ py: { xs: 4, md: 6 } }}>
              {error && (
                <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.25)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'error.main' }}>{error}</Typography>
                  <Button size="small" sx={{ color: 'error.main', minWidth: 'auto', p: 0.5 }} onClick={() => setError(null)}>✕</Button>
                </Box>
              )}
              <DocumentUpload onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} isProcessing={isProcessing} setIsProcessing={setIsProcessing} />
            </Container>
          </Box>
        ) : (
          <Container maxWidth="xl" sx={{ py: 3, px: { xs: 2, md: 3 } }}>
            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, gap: 3, alignItems: 'flex-start' }}>
              <Box sx={{ flex: '1 1 58%', minWidth: 0 }}>
                <AnalysisResults result={analysisResult} onNewDocument={handleNewDocument} />
              </Box>
              <Box sx={{ flex: '1 1 42%', minWidth: 0, position: { lg: 'sticky' }, top: { lg: '80px' }, maxHeight: { lg: 'calc(100vh - 100px)' }, display: 'flex', flexDirection: 'column' }}>
                <QAInterface documentId={analysisResult.document_id} />
              </Box>
            </Box>
          </Container>
        )}
      </Box>
    </ThemeProvider>
  );
}

export default App;
