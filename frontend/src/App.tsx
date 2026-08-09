import React, { useState, useMemo, useCallback } from 'react';
import { ThemeProvider, CssBaseline, Box, Container, Typography, Button, IconButton, Tooltip } from '@mui/material';
import { DarkModeOutlined, LightModeOutlined } from '@mui/icons-material';
import DocumentUpload from './components/DocumentUpload';
import AnalysisResults from './components/AnalysisResults';
import QAInterface from './components/QAInterface';
import { Eyebrow } from './components/Annotation';
import { buildTheme, Mode, MONO, DISPLAY } from './theme';
import { AnalysisResult } from './types/api';

/** What the knowledge base actually holds — the trust argument, in real numbers. */
const CORPUS = [
  { n: '1,791', label: 'statute sections', note: '11 bare Acts + the Constitution' },
  { n: '7,168', label: 'judgment passages', note: 'Supreme Court of India' },
  { n: '30', label: 'red-flag clauses', note: 'patterns drafted against you' },
  { n: '74', label: 'definitions & model clauses', note: 'plain-English references' },
];

/**
 * The hero specimen: one real clause from a rent deed with the annotation Legal EASE
 * would put beside it. The product's output *is* the hero — it argues the thesis
 * instead of describing it. The margin note arrives a beat after the clause, the way a
 * reader annotates: read first, then write.
 */
const Specimen: React.FC = () => (
  <Box
    sx={(theme) => ({
      mt: { xs: 6, md: 8 },
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: 2,
      bgcolor: 'background.paper',
      overflow: 'hidden',
      '@keyframes riseIn': { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
    })}
  >
    <Box sx={{ px: { xs: 2.5, md: 3 }, py: 1.25, borderBottom: (t) => `1px solid ${t.palette.divider}`, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
      <Eyebrow>Specimen · residential lease</Eyebrow>
      <Eyebrow sx={{ display: { xs: 'none', sm: 'block' } }}>clause 9(b)</Eyebrow>
    </Box>

    <Box sx={{ p: { xs: 2.5, md: 4 }, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '160px 1px 1fr' }, columnGap: { md: 3.5 }, rowGap: 2 }}>
      {/* Margin */}
      <Box sx={{ textAlign: { md: 'right' }, opacity: 0, animation: 'riseIn .5s .75s ease forwards' }}>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.72rem', fontWeight: 600, color: 'primary.main', lineHeight: 1.5 }}>
          S. 74 · Contract Act
        </Typography>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.65rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'text.secondary', mt: 0.5 }}>
          high risk
        </Typography>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.68rem', color: 'text.secondary', mt: 2 }}>
          AIR 2013 SC 3037
        </Typography>
      </Box>

      <Box sx={{ display: { xs: 'none', md: 'block' }, bgcolor: 'primary.main', opacity: 0.4 }} />

      {/* Clause + finding */}
      <Box sx={{ minWidth: 0 }}>
        <Typography
          sx={{
            fontFamily: DISPLAY, fontSize: { xs: '1.05rem', md: '1.2rem' }, fontStyle: 'italic',
            lineHeight: 1.6, color: 'text.primary', opacity: 0, animation: 'riseIn .5s .15s ease forwards',
          }}
        >
          “If the Lessee vacates the premises before expiry of the term, the entire security
          deposit of ₹50,000 shall stand forfeited to the Lessor.”
        </Typography>
        <Typography
          variant="body2"
          sx={{ mt: 2.5, color: 'text.secondary', maxWidth: '54ch', opacity: 0, animation: 'riseIn .5s .95s ease forwards' }}
        >
          Forfeiting the whole deposit is a penalty, not a genuine estimate of the landlord’s loss.
          Under Section 74 you owe reasonable compensation for loss actually proven — not a fixed
          sum fixed in advance. Ask for the clause to be capped at one month’s rent.
        </Typography>
      </Box>
    </Box>
  </Box>
);

function App() {
  const [mode, setMode] = useState<Mode>(() => (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [filename, setFilename] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const theme = useMemo(() => buildTheme(mode), [mode]);

  const handleUploadSuccess = useCallback((result: AnalysisResult, name: string) => {
    setAnalysisResult(result);
    setFilename(name);
    setError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleUploadError = useCallback((message: string) => {
    setError(message || null);
    setAnalysisResult(null);
  }, []);

  const handleNewDocument = useCallback(() => {
    setAnalysisResult(null);
    setFilename('');
    setError(null);
  }, []);

  const scrollToUpload = () => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      {/* ── Masthead ─────────────────────────────────────────────────────── */}
      <Box
        component="header"
        sx={(t) => ({
          position: 'sticky', top: 0, zIndex: 20,
          borderBottom: `1px solid ${t.palette.divider}`,
          bgcolor: t.palette.mode === 'dark' ? 'rgba(16,20,24,0.88)' : 'rgba(228,234,230,0.88)',
          backdropFilter: 'blur(12px)',
        })}
      >
        <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, py: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, minWidth: 0 }}>
            <Typography sx={{ fontFamily: MONO, fontWeight: 600, fontSize: '0.95rem', letterSpacing: '0.06em', color: 'text.primary' }}>
              §&nbsp;LEGAL&nbsp;EASE
            </Typography>
            <Typography sx={{ display: { xs: 'none', sm: 'block' }, fontFamily: MONO, fontSize: '0.68rem', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'text.secondary' }}>
              contracts read against Indian law
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title={mode === 'dark' ? 'Light theme' : 'Dark theme'}>
              <IconButton size="small" onClick={() => setMode((m) => (m === 'dark' ? 'light' : 'dark'))} sx={{ color: 'text.secondary' }} aria-label="Switch theme">
                {mode === 'dark' ? <LightModeOutlined sx={{ fontSize: 19 }} /> : <DarkModeOutlined sx={{ fontSize: 19 }} />}
              </IconButton>
            </Tooltip>
            {analysisResult ? (
              <Button size="small" variant="outlined" onClick={handleNewDocument}>Read another</Button>
            ) : (
              <Button size="small" variant="contained" onClick={scrollToUpload}>Read my contract</Button>
            )}
          </Box>
        </Container>
      </Box>

      <Box component="main" sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        {!analysisResult ? (
          <>
            {/* ── Hero ───────────────────────────────────────────────────── */}
            <Container maxWidth="lg" sx={{ pt: { xs: 7, md: 12 }, pb: { xs: 4, md: 6 } }}>
              <Eyebrow sx={{ color: 'primary.main', mb: 3 }}>Before you sign</Eyebrow>

              <Typography variant="h1" sx={{ maxWidth: '16ch' }}>
                Read the{' '}
                <Box component="em" sx={{ fontStyle: 'italic', color: 'primary.main' }}>margin</Box>
                , not just the contract.
              </Typography>

              <Typography variant="body1" sx={{ mt: 4, maxWidth: '58ch', color: 'text.secondary', fontSize: '1.05rem' }}>
                Upload the agreement you were handed. Legal EASE marks the clauses that work
                against you and puts the Indian statute or judgment that says so right beside
                each one — so you know what to argue, not just that something feels off.
              </Typography>

              <Box sx={{ mt: 4.5, display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                <Button variant="contained" size="large" onClick={scrollToUpload}>Read my contract</Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => window.open('https://wa.me/14155238886?text=join%20legal-ease-demo', '_blank', 'noopener')}
                >
                  Send one on WhatsApp
                </Button>
              </Box>

              <Specimen />
            </Container>

            {/* ── What it reads against ──────────────────────────────────── */}
            <Container maxWidth="lg" sx={{ py: { xs: 5, md: 7 } }}>
              <Eyebrow sx={{ mb: 3 }}>What it reads against</Eyebrow>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' },
                  borderTop: (t) => `1px solid ${t.palette.divider}`,
                }}
              >
                {CORPUS.map((c) => (
                  <Box key={c.label} sx={(t) => ({ py: 3, pr: 3, borderBottom: `1px solid ${t.palette.divider}` })}>
                    <Typography sx={{ fontFamily: DISPLAY, fontSize: '2rem', lineHeight: 1, color: 'text.primary' }}>{c.n}</Typography>
                    <Typography sx={{ fontFamily: MONO, fontSize: '0.68rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'primary.main', mt: 1.25 }}>
                      {c.label}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.75 }}>{c.note}</Typography>
                  </Box>
                ))}
              </Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 2.5, maxWidth: '62ch' }}>
                Every passage is embedded with InLegalBERT, a language model trained on Indian legal
                text, and retrieved at question time. Answers quote this corpus rather than the
                model’s own recollection of the law.
              </Typography>
            </Container>

            {/* ── Upload ─────────────────────────────────────────────────── */}
            <Container maxWidth="md" id="upload" sx={{ pb: { xs: 8, md: 12 }, pt: { xs: 2, md: 3 } }}>
              {error && (
                <Box
                  role="alert"
                  sx={(t) => ({
                    mb: 3, px: 2.5, py: 2, borderRadius: 1.5,
                    border: `1px solid ${t.palette.primary.main}`,
                    borderLeft: `3px solid ${t.palette.primary.main}`,
                    bgcolor: t.palette.mode === 'dark' ? 'rgba(218,102,115,0.08)' : 'rgba(140,29,45,0.05)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2,
                  })}
                >
                  <Box>
                    <Eyebrow sx={{ color: 'primary.main' }}>Couldn’t read that file</Eyebrow>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>{error}</Typography>
                  </Box>
                  <Button size="small" onClick={() => setError(null)} sx={{ color: 'text.secondary', minWidth: 'auto' }}>Dismiss</Button>
                </Box>
              )}
              <DocumentUpload
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
                isProcessing={isProcessing}
                setIsProcessing={setIsProcessing}
              />
            </Container>
          </>
        ) : (
          /* ── Reading view ─────────────────────────────────────────────── */
          <Container maxWidth="xl" sx={{ py: { xs: 3, md: 4 } }}>
            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, gap: { xs: 4, lg: 5 }, alignItems: 'flex-start' }}>
              <Box sx={{ flex: '1 1 62%', minWidth: 0, width: '100%' }}>
                <AnalysisResults result={analysisResult} filename={filename} onNewDocument={handleNewDocument} />
              </Box>
              <Box
                sx={{
                  flex: '1 1 38%', minWidth: 0, width: '100%',
                  position: { lg: 'sticky' }, top: { lg: 88 },
                  height: { lg: 'calc(100vh - 116px)' },
                  display: 'flex', flexDirection: 'column',
                }}
              >
                <QAInterface documentId={analysisResult.document_id} />
              </Box>
            </Box>
          </Container>
        )}
      </Box>

      {/* ── Colophon ───────────────────────────────────────────────────── */}
      <Box component="footer" sx={(t) => ({ borderTop: `1px solid ${t.palette.divider}`, py: 3, mt: 4 })}>
        <Container maxWidth="lg" sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'space-between' }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', maxWidth: '64ch' }}>
            Legal EASE explains documents. It is not a substitute for a lawyer, and nothing here is
            legal advice. Uploaded files are held only for your session and then deleted.
          </Typography>
          <Typography sx={{ fontFamily: MONO, fontSize: '0.68rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'text.secondary' }}>
            Gemini · InLegalBERT · Chroma
          </Typography>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
