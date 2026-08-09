import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ThemeProvider, CssBaseline, Box, Container, Typography, Button } from '@mui/material';
import { buildTheme, MONO } from '../theme';

interface Props { children: ReactNode; }
interface State { hasError: boolean; error: Error | null; errorInfo: ErrorInfo | null; }

/**
 * Renders when the app itself has thrown, so it carries its own theme rather than
 * relying on the provider inside App.
 */
class ErrorBoundary extends Component<Props, State> {
  public state: State = { hasError: false, error: null, errorInfo: null };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  public render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <ThemeProvider theme={buildTheme('dark')}>
        <CssBaseline />
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', display: 'flex', alignItems: 'center' }}>
          <Container maxWidth="sm">
            <Typography variant="overline" sx={{ color: 'primary.main' }}>Something broke</Typography>
            <Typography variant="h2" sx={{ mt: 1.5 }}>Legal EASE stopped mid-read.</Typography>
            <Typography variant="body1" sx={{ mt: 2.5, color: 'text.secondary' }}>
              Nothing was saved and your document was not stored. Reload and try the file again.
            </Typography>

            <Box sx={{ mt: 4, display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <Button variant="contained" onClick={() => window.location.reload()}>Reload</Button>
              <Button variant="outlined" onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}>
                Try again
              </Button>
            </Box>

            <Typography sx={{ fontFamily: MONO, fontSize: '0.7rem', color: 'text.secondary', mt: 4, wordBreak: 'break-word' }}>
              {this.state.error?.message || 'Unknown error'}
            </Typography>

            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <Box component="pre" sx={{ fontFamily: MONO, fontSize: '0.65rem', color: 'text.secondary', mt: 2, overflow: 'auto', maxHeight: 260 }}>
                {this.state.error?.stack}
                {this.state.errorInfo.componentStack}
              </Box>
            )}
          </Container>
        </Box>
      </ThemeProvider>
    );
  }
}

export default ErrorBoundary;
