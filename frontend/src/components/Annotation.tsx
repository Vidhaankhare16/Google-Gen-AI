import React from 'react';
import { Box, Typography } from '@mui/material';
import { MONO, bandColor } from '../theme';
import { LegalSource } from '../types/api';

/**
 * The margin rule — this app's one structural device.
 *
 * A lawyer reading your contract writes in the margin: the finding on the page, the
 * authority beside it. Every finding, warning and answer in Legal EASE is laid out that
 * way, so the retrieved law is part of the structure rather than a footnote. On narrow
 * screens the margin folds above the text and the rule becomes a coloured left edge.
 */

type Band = 'high' | 'medium' | 'low' | 'neutral';

const MARGIN_WIDTH = 150;

interface AnnotatedProps {
  /** Short authority for the margin, e.g. "S. 74 · Contract Act". */
  margin?: React.ReactNode;
  /** Optional second margin line, e.g. the severity or a citation year. */
  marginSub?: React.ReactNode;
  band?: Band;
  children: React.ReactNode;
}

export const Annotated: React.FC<AnnotatedProps> = ({ margin, marginSub, band = 'neutral', children }) => (
  <Box
    sx={(theme) => {
      const edge = band === 'neutral' ? theme.palette.divider : bandColor(theme, band);
      return {
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: `${MARGIN_WIDTH}px 1px 1fr` },
        columnGap: { md: 3 },
        rowGap: { xs: 1, md: 0 },
        py: 2.25,
        // Narrow screens lose the true margin, so the authority colour moves to the edge.
        borderLeft: { xs: `2px solid ${edge}`, md: 'none' },
        pl: { xs: 2, md: 0 },
      };
    }}
  >
    {/* Margin column */}
    <Box sx={{ textAlign: { md: 'right' }, pt: { md: 0.25 } }}>
      {margin && (
        <Typography
          component="div"
          sx={{ fontFamily: MONO, fontSize: '0.7rem', fontWeight: 500, lineHeight: 1.5, color: (t) => (band === 'neutral' ? t.palette.text.secondary : bandColor(t, band)) }}
        >
          {margin}
        </Typography>
      )}
      {marginSub && (
        <Typography component="div" sx={{ fontFamily: MONO, fontSize: '0.65rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'text.secondary', mt: 0.5, opacity: 0.85 }}>
          {marginSub}
        </Typography>
      )}
    </Box>

    {/* The rule itself */}
    <Box
      sx={(theme) => ({
        display: { xs: 'none', md: 'block' },
        bgcolor: band === 'neutral' ? theme.palette.divider : bandColor(theme, band),
        opacity: band === 'neutral' ? 1 : 0.55,
      })}
    />

    <Box sx={{ minWidth: 0 }}>{children}</Box>
  </Box>
);

/** Structural label: mono, letterspaced, uppercase. Used for every section and field. */
export const Eyebrow: React.FC<{ children: React.ReactNode; color?: string; sx?: object }> = ({ children, color, sx }) => (
  <Typography variant="overline" component="div" sx={{ color: color ?? 'text.secondary', ...sx }}>
    {children}
  </Typography>
);

/** A section heading: eyebrow + count, sitting on the same grid as the margin rule. */
export const SectionHead: React.FC<{ label: string; count?: number; note?: string }> = ({ label, count, note }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: `${MARGIN_WIDTH}px 1px 1fr` }, columnGap: { md: 3 }, alignItems: 'baseline', pb: 1.5, pt: 4 }}>
    <Eyebrow sx={{ textAlign: { md: 'right' } }}>{label}</Eyebrow>
    <Box />
    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, minWidth: 0 }}>
      {typeof count === 'number' && (
        <Typography sx={{ fontFamily: MONO, fontSize: '0.7rem', color: 'text.secondary' }}>
          {String(count).padStart(2, '0')}
        </Typography>
      )}
      {note && (
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          {note}
        </Typography>
      )}
    </Box>
  </Box>
);

/** Condense a retrieved source into the one line that belongs in a margin. */
export const citeLine = (s: LegalSource): string => {
  if (s.type === 'judgment') return s.citation || s.source || 'Precedent';
  if (s.type === 'statute') {
    const act = (s.source || '').replace(/^The\s+/i, '').replace(/,?\s*\d{4}$/, '');
    return [s.section, act].filter(Boolean).join(' · ');
  }
  return s.section || s.source || 'Reference';
};

/** What kind of authority a source is, spelled out for the margin's second line. */
export const citeKind = (s: LegalSource): string =>
  ({ statute: 'statute', judgment: 'precedent', redflag: 'red flag', glossary: 'definition', template: 'model clause' } as Record<string, string>)[s.type || ''] || 'source';

export default Annotated;
