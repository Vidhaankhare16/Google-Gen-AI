import React, { useState } from 'react';
import { Box, Typography, Button, Tooltip } from '@mui/material';
import { AnalysisResult, LegalSource } from '../types/api';
import ApiService from '../services/api';
import { Annotated, Eyebrow, SectionHead, citeLine } from './Annotation';
import { MONO, DISPLAY, riskBand, bandColor } from '../theme';

interface AnalysisResultsProps {
  result: AnalysisResult;
  filename?: string;
  onNewDocument: () => void;
}

const BAND_WORD = { high: 'high risk', medium: 'some risk', low: 'low risk' } as const;

/**
 * The risk meter: ten ticks read left to right, filled to the score. A ruler rather than
 * a dial — it belongs to the world of stamp duty schedules and rent slabs, and it reads
 * at a glance without pretending to be a dashboard.
 */
const RiskMeter: React.FC<{ score: number }> = ({ score }) => {
  const s = Math.min(Math.max(Math.round(score), 0), 10);
  const band = riskBand(s);
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
        <Typography sx={{ fontFamily: DISPLAY, fontSize: '3rem', lineHeight: 0.85, color: (t) => bandColor(t, band) }}>{s}</Typography>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.7rem', color: 'text.secondary' }}>/10</Typography>
      </Box>
      <Box sx={{ pb: 0.5 }}>
        <Box sx={{ display: 'flex', gap: '3px' }} aria-hidden>
          {Array.from({ length: 10 }, (_, i) => (
            <Box
              key={i}
              sx={(t) => ({
                width: 12, height: i < s ? 18 : 10, alignSelf: 'flex-end',
                bgcolor: i < s ? bandColor(t, band) : t.palette.divider,
                transition: `height .4s ${i * 45}ms ease, background-color .4s`,
              })}
            />
          ))}
        </Box>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.68rem', letterSpacing: '0.12em', textTransform: 'uppercase', color: (t) => bandColor(t, band), mt: 1 }}>
          {BAND_WORD[band]}
        </Typography>
      </Box>
    </Box>
  );
};

const severityOf = (w: string): 'high' | 'medium' | 'low' => {
  const u = w.toUpperCase();
  if (u.startsWith('[HIGH]')) return 'high';
  if (u.startsWith('[MEDIUM]')) return 'medium';
  return 'low';
};
const stripSeverity = (w: string) => w.replace(/^\[(HIGH|MEDIUM|LOW)\]\s*/i, '');

/** Group retrieved authorities by kind so statutes don't get lost among judgments. */
const groupSources = (sources: LegalSource[]): Array<[string, LegalSource[]]> => {
  const order = ['statute', 'judgment', 'redflag', 'glossary', 'template'];
  const groups: Record<string, LegalSource[]> = {};
  sources.forEach((s) => {
    const k = s.type || 'other';
    groups[k] = (groups[k] || []).concat(s);
  });
  return Object.keys(groups)
    .sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .map((k): [string, LegalSource[]] => [k, groups[k]]);
};

const KIND_HEADING: Record<string, string> = {
  statute: 'Statute',
  judgment: 'Precedent',
  redflag: 'Red-flag pattern',
  glossary: 'Definition',
  template: 'Model clause',
  other: 'Reference',
};

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ result, filename, onNewDocument }) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try { await ApiService.deleteDocument(result.document_id); } catch { /* the session copy expires anyway */ }
    setIsDeleting(false);
    onNewDocument();
  };

  const riskScore = typeof result.risk_score === 'number' ? result.risk_score : 5;
  const documentType = result.document_type ?? 'Legal document';
  const keyPoints = result.key_points ?? [];
  const warnings = result.warnings ?? [];
  const sources = result.sources ?? [];

  // Warnings read worst-first: that is the order someone renegotiating would work in.
  const rank = { high: 0, medium: 1, low: 2 };
  const orderedWarnings = [...warnings].sort((a, b) => rank[severityOf(a)] - rank[severityOf(b)]);

  return (
    <Box sx={{ '@keyframes riseIn': { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } }, animation: 'riseIn .4s ease' }}>
      {/* ── Document bar ───────────────────────────────────────────────── */}
      <Box sx={(t) => ({ pb: 3, borderBottom: `1px solid ${t.palette.divider}` })}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ minWidth: 0 }}>
            <Eyebrow sx={{ color: 'primary.main' }}>{documentType}</Eyebrow>
            <Typography variant="h2" sx={{ mt: 1 }}>What this asks of you</Typography>
            {filename && (
              <Typography sx={{ fontFamily: MONO, fontSize: '0.7rem', color: 'text.secondary', mt: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {filename}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            <Button size="small" variant="outlined" onClick={onNewDocument}>Read another</Button>
            <Tooltip title="Erase this document from the server now">
              <Button size="small" variant="outlined" onClick={handleDelete} disabled={isDeleting} sx={{ color: 'primary.main', borderColor: 'primary.main' }}>
                {isDeleting ? 'Erasing…' : 'Erase now'}
              </Button>
            </Tooltip>
          </Box>
        </Box>

        <Box sx={{ mt: 3.5 }}>
          <RiskMeter score={riskScore} />
        </Box>
      </Box>

      {/* ── Summary ────────────────────────────────────────────────────── */}
      <SectionHead label="In short" />
      <Annotated margin="the gist">
        <Typography sx={{ fontFamily: DISPLAY, fontSize: { xs: '1.1rem', md: '1.25rem' }, lineHeight: 1.6, color: 'text.primary' }}>
          {result.summary || 'No summary came back for this document.'}
        </Typography>
      </Annotated>

      {/* ── Warnings ───────────────────────────────────────────────────── */}
      {orderedWarnings.length > 0 && (
        <>
          <SectionHead label="Push back on" count={orderedWarnings.length} note="worst first" />
          <Box sx={{ borderTop: (t) => `1px solid ${t.palette.divider}` }}>
            {orderedWarnings.map((warning, i) => {
              const sev = severityOf(warning);
              return (
                <Box key={i} sx={(t) => ({ borderBottom: `1px solid ${t.palette.divider}` })}>
                  <Annotated band={sev} margin={`risk ${String(i + 1).padStart(2, '0')}`} marginSub={sev}>
                    <Typography variant="body1" sx={{ color: 'text.primary' }}>{stripSeverity(warning)}</Typography>
                  </Annotated>
                </Box>
              );
            })}
          </Box>
        </>
      )}

      {/* ── Key points ─────────────────────────────────────────────────── */}
      {keyPoints.length > 0 && (
        <>
          <SectionHead label="What it says" count={keyPoints.length} />
          <Box sx={{ borderTop: (t) => `1px solid ${t.palette.divider}` }}>
            {keyPoints.map((point, i) => (
              <Box key={i} sx={(t) => ({ borderBottom: `1px solid ${t.palette.divider}` })}>
                <Annotated margin={String(i + 1).padStart(2, '0')}>
                  <Typography variant="body1" sx={{ color: 'text.primary' }}>{point}</Typography>
                </Annotated>
              </Box>
            ))}
          </Box>
        </>
      )}

      {/* ── Authorities ────────────────────────────────────────────────── */}
      {sources.length > 0 && (
        <>
          <SectionHead label="Read against" count={sources.length} note="retrieved from the corpus for this document" />
          <Box sx={{ borderTop: (t) => `1px solid ${t.palette.divider}` }}>
            {groupSources(sources).map(([kind, items]) => (
              <Box key={kind} sx={(t) => ({ borderBottom: `1px solid ${t.palette.divider}` })}>
                <Annotated margin={KIND_HEADING[kind] || kind} marginSub={`${items.length}`}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {items.map((s, i) => {
                      const label = citeLine(s);
                      // Only append the source when it adds something: for a judgment with
                      // no citation, citeLine already *is* the case name.
                      const trailing = s.source && s.type !== 'statute' && s.source !== label ? s.source : null;
                      return (
                      <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, alignItems: 'baseline' }}>
                        <Typography variant="body2" sx={{ color: 'text.primary', minWidth: 0 }}>
                          {label}
                          {trailing && <Box component="span" sx={{ color: 'text.secondary' }}> — {trailing}</Box>}
                        </Typography>
                        {typeof s.score === 'number' && (
                          <Tooltip title="Cosine similarity to this document">
                            <Typography sx={{ fontFamily: MONO, fontSize: '0.66rem', color: 'text.secondary', flexShrink: 0 }}>
                              {s.score.toFixed(2)}
                            </Typography>
                          </Tooltip>
                        )}
                      </Box>
                      );
                    })}
                  </Box>
                </Annotated>
              </Box>
            ))}
          </Box>
        </>
      )}

      <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 4, maxWidth: '68ch' }}>
        These findings describe the document, they don’t settle it. Take anything marked{' '}
        <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>high risk</Box> to a lawyer before you sign.
      </Typography>
    </Box>
  );
};

export default AnalysisResults;
