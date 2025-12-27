import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Paper,
  Alert,
  Chip,
  AppBar,
  Toolbar,
  CssBaseline,
  ThemeProvider,
  createTheme,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { Gavel, AutoAwesome, ArrowForward } from '@mui/icons-material';

import DocumentUpload from './components/DocumentUpload';
import AnalysisResults from './components/AnalysisResults';
import QAInterface from './components/QAInterface';
import { AnalysisResult } from './types/api';

// Create a clean, modern theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
    },
    text: {
      primary: '#2c3e50',
      secondary: '#7f8c8d',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '3.5rem',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '2.5rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h6: {
      fontWeight: 600,
    },
    body1: {
      fontSize: '1.1rem',
      lineHeight: 1.6,
    },
  },
  shape: {
    borderRadius: 12,
  },
});

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  backgroundColor: '#ffffff',
  color: theme.palette.text.primary,
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  borderBottom: '1px solid #e0e0e0',
}));

const HeroSection = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(8, 0, 6, 0),
  background: 'linear-gradient(180deg, #fafafa 0%, #ffffff 100%)',
}));

const MainContent = styled(Container)(({ theme }) => ({
  maxWidth: '800px !important',
  margin: '0 auto',
  padding: theme.spacing(0, 2),
}));

const AnalysisSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  marginTop: theme.spacing(4),
  borderRadius: theme.spacing(2),
  boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  border: '1px solid #e0e0e0',
}));

const FeatureBadge = styled(Chip)(({ theme }) => ({
  backgroundColor: '#e3f2fd',
  color: '#1976d2',
  fontWeight: 500,
  marginBottom: theme.spacing(3),
}));

function App() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUploadSuccess = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
    setAnalysisResult(null);
  };

  const handleNewDocument = () => {
    setAnalysisResult(null);
    setError(null);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="App">
        {/* Header */}
        <StyledAppBar position="static" elevation={0}>
          <Toolbar sx={{ justifyContent: 'space-between', py: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  backgroundColor: '#1976d2',
                  borderRadius: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2,
                }}
              >
                <Gavel sx={{ color: 'white', fontSize: 20 }} />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#2c3e50' }}>
                Legal Ease
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
              <Typography variant="body2" sx={{ color: 'text.secondary', cursor: 'pointer' }}>
                Features
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', cursor: 'pointer' }}>
                How it Works
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', cursor: 'pointer' }}>
                Pricing
              </Typography>
              <Button variant="text" sx={{ color: 'text.secondary' }}>
                Sign in
              </Button>
              <Button variant="contained" size="small" sx={{ borderRadius: 2 }}>
                Get Started
              </Button>
            </Box>
          </Toolbar>
        </StyledAppBar>

        {/* Main Content */}
        <MainContent>
          {!analysisResult ? (
            <>
              {/* Hero Section */}
              <HeroSection>
                <FeatureBadge
                  icon={<AutoAwesome sx={{ fontSize: 16 }} />}
                  label="AI-Powered Legal Document Analysis"
                />
                
                <Typography variant="h1" component="h1" gutterBottom sx={{ mb: 3 }}>
                  Demystify Complex{' '}
                  <Box component="span" sx={{ color: 'primary.main' }}>
                    Legal Documents
                  </Box>{' '}
                  with AI
                </Typography>
                
                <Typography variant="body1" sx={{ color: 'text.secondary', mb: 4, maxWidth: 600, mx: 'auto' }}>
                  Transform impenetrable legal jargon into clear, actionable guidance.
                  Understand rental agreements, contracts, and terms of service before you sign.
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mb: 4 }}>
                  <Button
                    variant="contained"
                    size="large"
                    endIcon={<ArrowForward />}
                    sx={{
                      px: 4,
                      py: 1.5,
                      borderRadius: 2,
                      textTransform: 'none',
                      fontSize: '1.1rem',
                      fontWeight: 600,
                    }}
                    onClick={() => document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth' })}
                  >
                    Analyze Document
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    sx={{
                      px: 4,
                      py: 1.5,
                      borderRadius: 2,
                      textTransform: 'none',
                      fontSize: '1.1rem',
                      fontWeight: 600,
                      borderColor: '#25D366',
                      color: '#25D366',
                      '&:hover': {
                        borderColor: '#25D366',
                        backgroundColor: 'rgba(37, 211, 102, 0.04)',
                      },
                    }}
                    onClick={() => window.open('https://wa.me/14155238886?text=join%20legal-ease-demo', '_blank')}
                  >
                    📱 Try WhatsApp Demo
                  </Button>
                </Box>

                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Free analysis for your first 3 documents • No credit card required
                </Typography>
                
                {/* WhatsApp Demo Info */}
                <Box sx={{ mt: 6, p: 3, backgroundColor: '#f0f7ff', borderRadius: 2, border: '1px solid #e3f2fd' }}>
                  <Typography variant="h6" sx={{ mb: 2, color: '#1976d2', fontWeight: 600 }}>
                    📱 WhatsApp Demo Available!
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                    Try Legal EASE directly on WhatsApp! Upload PDFs and get instant AI analysis on your phone.
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      1. Message: <strong>+1 (415) 523-8886</strong>
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      2. Send: <strong>"join legal-ease-demo"</strong>
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      3. Upload your PDF!
                    </Typography>
                  </Box>
                </Box>
              </HeroSection>

              {/* Upload Section */}
              <Box id="upload-section" sx={{ mt: 6 }}>
                {error && (
                  <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError(null)}>
                    {error}
                  </Alert>
                )}
                
                <DocumentUpload
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={handleUploadError}
                  isProcessing={isProcessing}
                  setIsProcessing={setIsProcessing}
                />
              </Box>
            </>
          ) : (
            <>
              {/* Analysis Results */}
              <AnalysisSection elevation={0}>
                <AnalysisResults
                  result={analysisResult}
                  onNewDocument={handleNewDocument}
                />
              </AnalysisSection>

              {/* Q&A Section */}
              <AnalysisSection elevation={0}>
                <QAInterface documentId={analysisResult.document_id} />
              </AnalysisSection>
            </>
          )}
        </MainContent>
      </div>
    </ThemeProvider>
  );
}

export default App;