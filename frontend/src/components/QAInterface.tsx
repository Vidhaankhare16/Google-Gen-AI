import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, TextField, Button, CircularProgress } from '@mui/material';
import { ArrowUpward } from '@mui/icons-material';
import ApiService from '../services/api';
import { QuestionAnswer } from '../types/api';
import { Eyebrow, citeLine, citeKind } from './Annotation';
import { MONO, DISPLAY, bandColor } from '../theme';

const CONFIDENCE_NOTE: Record<string, string> = {
  high: 'the document is explicit on this',
  medium: 'the document implies this',
  low: 'the document barely covers this',
};

const OPENERS = [
  'What am I agreeing to do?',
  'How do I get out of this?',
  'What happens if I pay late?',
  'Can they change the terms later?',
  'Is anything here unenforceable?',
];

interface QAInterfaceProps { documentId: string; }

/**
 * Counsel: a question put to the document, answered from retrieved clauses with the
 * authority set in the margin — the same device the findings use, so an answer and a
 * finding are visibly the same kind of object.
 */
const QAInterface: React.FC<QAInterfaceProps> = ({ documentId }) => {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<QuestionAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [history, isLoading]);

  const submit = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || isLoading) return;
    setQuestion(''); setIsLoading(true); setError(null);
    try {
      const res = await ApiService.askQuestion(documentId, trimmed);
      if (res.success && res.answer) {
        setHistory((prev) => [...prev, {
          question: trimmed,
          answer: res.answer!,
          source_section: res.source_section,
          sources: res.sources,
          confidence: res.confidence || 'medium',
          document_id: documentId,
          answered_at: res.answered_at || new Date().toISOString(),
        }]);
      } else {
        throw new Error((res as any)?.error?.message || 'No answer came back. Ask again.');
      }
    } catch (err: any) {
      setError(err.message || 'That question could not be answered. Ask again.');
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  };

  const unused = OPENERS.filter((q) => !history.some((h) => h.question === q));

  return (
    <Box
      sx={(t) => ({
        display: 'flex', flexDirection: 'column',
        height: { xs: 'auto', lg: '100%' }, minHeight: { xs: 480, lg: 0 },
        border: `1px solid ${t.palette.divider}`, borderRadius: 2,
        bgcolor: 'background.paper', overflow: 'hidden',
      })}
    >
      {/* Header */}
      <Box sx={(t) => ({ px: 3, py: 2, borderBottom: `1px solid ${t.palette.divider}`, flexShrink: 0 })}>
        <Eyebrow sx={{ color: 'primary.main' }}>Counsel</Eyebrow>
        <Typography sx={{ fontFamily: DISPLAY, fontSize: '1.3rem', mt: 0.5, lineHeight: 1.25 }}>Ask this document</Typography>
      </Box>

      {/* Transcript */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 3, py: 2.5, minHeight: 0 }}>
        {history.length === 0 && !isLoading && (
          <Box>
            <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: '40ch' }}>
              Questions are answered from the clauses in your file, with the Indian law they turn on
              set beside the answer. Start with one of these, or write your own.
            </Typography>
            <Box sx={{ mt: 2.5, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.25 }}>
              {OPENERS.map((q) => (
                <Button
                  key={q}
                  onClick={() => submit(q)}
                  sx={{
                    px: 0, py: 0.75, justifyContent: 'flex-start', textAlign: 'left', color: 'text.primary',
                    fontWeight: 400, fontSize: '0.9rem',
                    '&:hover': { background: 'none', color: 'primary.main' },
                  }}
                >
                  <Box component="span" sx={{ fontFamily: MONO, fontSize: '0.7rem', color: 'primary.main', mr: 1.5 }}>→</Box>
                  {q}
                </Button>
              ))}
            </Box>
          </Box>
        )}

        {history.map((qa, idx) => (
          <Box key={idx} sx={{ mb: 4 }}>
            {/* The question, set as a heading — it is the thing being answered. */}
            <Typography sx={{ fontFamily: DISPLAY, fontSize: '1.1rem', fontStyle: 'italic', lineHeight: 1.45, color: 'text.primary' }}>
              {qa.question}
            </Typography>

            <Box sx={(t) => ({ mt: 1.75, pl: 2, borderLeft: `2px solid ${t.palette.divider}` })}>
              <Typography variant="body2" sx={{ color: 'text.primary' }}>{qa.answer}</Typography>

              {qa.source_section && (
                <Typography variant="caption" sx={{ display: 'block', mt: 1.5, color: 'text.secondary' }}>
                  In your document: {qa.source_section}
                </Typography>
              )}

              {/* Authorities in the margin position — mono, stacked, quiet. */}
              {qa.sources && qa.sources.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Eyebrow>Read against</Eyebrow>
                  <Box sx={{ mt: 0.75, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {qa.sources.slice(0, 4).map((s, i) => (
                      <Typography
                        key={i}
                        title={[s.source, s.section, s.citation].filter(Boolean).join(' · ')}
                        sx={{ fontFamily: MONO, fontSize: '0.68rem', color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {citeLine(s)}
                        <Box component="span" sx={{ opacity: 0.6 }}> · {citeKind(s)}</Box>
                      </Typography>
                    ))}
                  </Box>
                </Box>
              )}

              <Typography sx={{ fontFamily: MONO, fontSize: '0.65rem', letterSpacing: '0.08em', textTransform: 'uppercase', mt: 2, color: (t) => bandColor(t, qa.confidence === 'high' ? 'low' : qa.confidence === 'low' ? 'high' : 'medium') }}>
                {CONFIDENCE_NOTE[qa.confidence] || CONFIDENCE_NOTE.medium}
              </Typography>
            </Box>
          </Box>
        ))}

        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1 }}>
            <Box sx={{ display: 'flex', gap: '4px' }}>
              {[0, 160, 320].map((d) => (
                <Box key={d} sx={{
                  width: 5, height: 5, borderRadius: '50%', bgcolor: 'primary.main',
                  '@keyframes pulseDot': { '0%,70%,100%': { opacity: 0.25 }, '35%': { opacity: 1 } },
                  animation: `pulseDot 1.3s ${d}ms infinite ease-in-out`,
                }} />
              ))}
            </Box>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>Looking through the clauses and the statutes…</Typography>
          </Box>
        )}

        {error && (
          <Box role="alert" sx={(t) => ({ mt: 2, px: 2, py: 1.5, borderLeft: `2px solid ${t.palette.primary.main}` })}>
            <Typography variant="body2" sx={{ color: 'primary.main' }}>{error}</Typography>
          </Box>
        )}

        <div ref={endRef} />
      </Box>

      {/* Follow-ups */}
      {history.length > 0 && !isLoading && unused.length > 0 && (
        <Box sx={(t) => ({ px: 3, py: 1.5, borderTop: `1px solid ${t.palette.divider}`, display: 'flex', flexWrap: 'wrap', gap: 1.5, flexShrink: 0 })}>
          {unused.slice(0, 2).map((q) => (
            <Button key={q} size="small" onClick={() => submit(q)} sx={{ p: 0, minWidth: 0, fontWeight: 400, fontSize: '0.78rem', color: 'text.secondary', '&:hover': { background: 'none', color: 'primary.main' } }}>
              {q}
            </Button>
          ))}
        </Box>
      )}

      {/* Ask */}
      <Box
        component="form"
        onSubmit={(e) => { e.preventDefault(); submit(question); }}
        sx={(t) => ({ p: 2, borderTop: `1px solid ${t.palette.divider}`, display: 'flex', gap: 1, flexShrink: 0 })}
      >
        <TextField
          inputRef={inputRef}
          fullWidth size="small" multiline maxRows={4}
          placeholder="Ask about a clause…"
          value={question}
          onChange={(e) => { setQuestion(e.target.value); if (error) setError(null); }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(question); } }}
          disabled={isLoading}
          inputProps={{ 'aria-label': 'Ask about a clause' }}
          sx={{ '& .MuiOutlinedInput-root': { fontSize: '0.9rem' } }}
        />
        <Button type="submit" variant="contained" disabled={!question.trim() || isLoading} aria-label="Ask" sx={{ minWidth: 44, px: 0, alignSelf: 'flex-end', height: 40 }}>
          {isLoading ? <CircularProgress size={15} color="inherit" /> : <ArrowUpward sx={{ fontSize: 18 }} />}
        </Button>
      </Box>
    </Box>
  );
};

export default QAInterface;
