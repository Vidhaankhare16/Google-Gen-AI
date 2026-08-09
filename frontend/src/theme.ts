import { createTheme, Theme } from '@mui/material/styles';

/**
 * Legal EASE design tokens.
 *
 * The visual language is borrowed from the documents themselves: Indian non-judicial
 * stamp paper (a pale blue-green, not a warm cream), fountain-pen ink, court-seal
 * oxblood, and the verdigris of an old brass seal. The three accents double as the
 * risk scale — high risk is the seal red, medium is brass, low is verdigris — so the
 * palette and the semantics are the same set of colours rather than two competing ones.
 */
export const tokens = {
  light: {
    ground: '#E4EAE6', // stamp paper
    surface: '#F5F8F6', // vellum
    surfaceSunken: '#DCE4DF',
    ink: '#14181C',
    inkMuted: '#57646E',
    rule: 'rgba(20, 24, 28, 0.14)',
    seal: '#8C1D2D', // court-seal oxblood — high risk, primary action
    brass: '#8A5F1F', // antique brass — medium risk, eyebrows
    verdigris: '#2A6153', // aged brass patina — low risk, confirmations
  },
  dark: {
    ground: '#101418',
    surface: '#171D22',
    surfaceSunken: '#0B0E11',
    ink: '#E9EEEB',
    inkMuted: '#94A0A9',
    rule: 'rgba(233, 238, 235, 0.14)',
    seal: '#DA6673',
    brass: '#D3A24E',
    verdigris: '#5FB79F',
  },
} as const;

export type Mode = 'light' | 'dark';

export const DISPLAY = '"Newsreader", Georgia, "Times New Roman", serif';
export const BODY = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif';
export const MONO = '"IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace';

/** Risk band for a 0–10 score, shared by the gauge, the meter and the finding rows. */
export const riskBand = (score: number): 'high' | 'medium' | 'low' =>
  score >= 7 ? 'high' : score >= 4 ? 'medium' : 'low';

/** The colour a risk band takes in the current theme. */
export const bandColor = (theme: Theme, band: 'high' | 'medium' | 'low'): string => {
  const t = tokens[theme.palette.mode as Mode];
  return band === 'high' ? t.seal : band === 'medium' ? t.brass : t.verdigris;
};

export const buildTheme = (mode: Mode) => {
  const t = tokens[mode];

  return createTheme({
    palette: {
      mode,
      primary: { main: t.seal },
      secondary: { main: t.verdigris },
      warning: { main: t.brass },
      error: { main: t.seal },
      success: { main: t.verdigris },
      background: { default: t.ground, paper: t.surface },
      text: { primary: t.ink, secondary: t.inkMuted },
      divider: t.rule,
    },

    typography: {
      fontFamily: BODY,
      // Display sizes are set in Newsreader at a light weight: a serif this large reads
      // as authoritative without the fashion-magazine contrast of a Didone.
      h1: { fontFamily: DISPLAY, fontWeight: 400, fontSize: 'clamp(2.6rem, 6vw, 4.25rem)', lineHeight: 1.03, letterSpacing: '-0.025em' },
      h2: { fontFamily: DISPLAY, fontWeight: 400, fontSize: 'clamp(1.9rem, 4vw, 2.6rem)', lineHeight: 1.12, letterSpacing: '-0.02em' },
      h3: { fontFamily: DISPLAY, fontWeight: 500, fontSize: '1.5rem', lineHeight: 1.25, letterSpacing: '-0.01em' },
      h4: { fontFamily: DISPLAY, fontWeight: 500, fontSize: '1.25rem', lineHeight: 1.3 },
      h5: { fontFamily: BODY, fontWeight: 700, fontSize: '1rem', letterSpacing: '-0.005em' },
      h6: { fontFamily: BODY, fontWeight: 700, fontSize: '0.875rem' },
      body1: { fontSize: '1rem', lineHeight: 1.7 },
      body2: { fontSize: '0.9rem', lineHeight: 1.65 },
      caption: { fontSize: '0.75rem', lineHeight: 1.5 },
      // The eyebrow: mono, letterspaced, uppercase. Used for every structural label.
      overline: { fontFamily: MONO, fontSize: '0.6875rem', fontWeight: 500, letterSpacing: '0.16em', textTransform: 'uppercase', lineHeight: 1.6 },
      button: { fontFamily: BODY, fontWeight: 600, letterSpacing: '0.01em' },
    },

    shape: { borderRadius: 8 },

    components: {
      MuiCssBaseline: {
        styleOverrides: {
          '*': { boxSizing: 'border-box' },
          html: { scrollBehavior: 'smooth' },
          body: { backgroundColor: t.ground },
          '::selection': { background: mode === 'dark' ? 'rgba(218,102,115,0.28)' : 'rgba(140,29,45,0.16)' },
          '::-webkit-scrollbar': { width: 10, height: 10 },
          '::-webkit-scrollbar-track': { background: 'transparent' },
          '::-webkit-scrollbar-thumb': { background: t.rule, borderRadius: 8, border: `3px solid ${t.ground}` },
          '::-webkit-scrollbar-thumb:hover': { background: t.inkMuted },
          '@media (prefers-reduced-motion: reduce)': {
            '*, *::before, *::after': { animationDuration: '0.01ms !important', animationIterationCount: '1 !important', transitionDuration: '0.01ms !important' },
          },
        },
      },

      MuiButton: {
        defaultProps: { disableElevation: true, disableRipple: false },
        styleOverrides: {
          root: { textTransform: 'none', borderRadius: 6, fontSize: '0.9rem', paddingInline: 18, transition: 'background-color .18s, border-color .18s, color .18s' },
          containedPrimary: {
            backgroundColor: t.seal,
            color: mode === 'dark' ? '#12171B' : '#FBFCFB',
            '&:hover': { backgroundColor: mode === 'dark' ? '#E4818C' : '#701725' },
            // A washed-out tint of the accent reads as a broken button; an inactive
            // control should look inactive, not like a faded active one.
            '&.Mui-disabled': {
              backgroundColor: 'transparent',
              color: t.inkMuted,
              boxShadow: `inset 0 0 0 1px ${t.rule}`,
            },
          },
          outlined: {
            borderColor: t.rule,
            color: t.ink,
            '&:hover': { borderColor: t.inkMuted, backgroundColor: mode === 'dark' ? 'rgba(233,238,235,0.04)' : 'rgba(20,24,28,0.035)' },
          },
        },
      },

      MuiChip: { styleOverrides: { root: { borderRadius: 4, fontWeight: 600, fontSize: '0.75rem' } } },

      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: 'none', border: `1px solid ${t.rule}` },
        },
      },

      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              backgroundColor: mode === 'dark' ? 'rgba(0,0,0,0.22)' : '#FFFFFF',
              borderRadius: 6,
              '& fieldset': { borderColor: t.rule },
              '&:hover fieldset': { borderColor: t.inkMuted },
              '&.Mui-focused fieldset': { borderColor: t.seal, borderWidth: 1 },
            },
          },
        },
      },

      MuiIconButton: { styleOverrides: { root: { borderRadius: 6 } } },

      MuiTooltip: {
        styleOverrides: {
          tooltip: { fontFamily: MONO, fontSize: '0.7rem', backgroundColor: t.ink, color: t.ground, borderRadius: 4, letterSpacing: '0.01em' },
        },
      },

      // A visible, unmistakable focus ring everywhere — the app is used by people
      // reading carefully, often with a keyboard.
      MuiButtonBase: {
        styleOverrides: {
          root: { '&:focus-visible': { outline: `2px solid ${t.seal}`, outlineOffset: 2 } },
        },
      },
    },
  });
};
