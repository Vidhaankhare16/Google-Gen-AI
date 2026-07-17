import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, TextField, Button, Chip, CircularProgress } from '@mui/material';
import { Send, ChatBubble, SmartToy, Person } from '@mui/icons-material';
import ApiService from '../services/api';
import { QuestionAnswer } from '../types/api';

const TypingIndicator = () => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, px: 0.5, py: 0.25 }}>
    {[0, 150, 300].map((delay, i) => (
      <Box key={i} sx={{
        width: 7, height: 7, borderRadius: '50%', bgcolor: 'primary.main', opacity: 0.7,
        '@keyframes typingBounce': {
          '0%, 60%, 100%': { transform: 'translateY(0)', opacity: 0.5 },
          '30%': { transform: 'translateY(-7px)', opacity: 1 },
        },
        animation: `typingBounce 1.2s ${delay}ms infinite ease-in-out`,
      }} />
    ))}
  </Box>
);

const CONFIDENCE_COLORS: Record<string, string> = { high: '#059669', medium: '#D97706', low: '#DC2626' };
const SUGGESTED = [
  'What are my key obligations?',
  'Are there any auto-renewal clauses?',
  'What are the termination conditions?',
  'What are the liability limitations?',
  'What happens if I miss a payment?',
];

interface QAInterfaceProps { documentId: string; }

const QAInterface: React.FC<QAInterfaceProps> = ({ documentId }) => {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [qaHistory, setQAHistory] = useState<QuestionAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [qaHistory, isLoading]);

  const submit = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || isLoading) return;
    setQuestion(''); setIsLoading(true); setError(null);
    try {
      const res = await ApiService.askQuestion(documentId, trimmed);
      if (res.success && res.answer) {
        setQAHistory(prev => [...prev, { question: trimmed, answer: res.answer!, source_section: res.source_section, confidence: res.confidence || 'medium', document_id: documentId, answered_at: res.answered_at || new Date().toISOString() }]);
      } else {
        throw new Error((res as any)?.error?.message || 'Failed to get answer');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to answer question. Please try again.');
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); submit(question); };
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(question); } };
  const unusedSuggestions = SUGGESTED.filter(q => !qaHistory.some(qa => qa.question === q));

  return (
    <Box sx={(theme) => ({
      display: 'flex', flexDirection: 'column',
      height: { xs: 'auto', lg: '100%' },
      minHeight: { xs: '520px', lg: 0 },
      bgcolor: 'background.paper',
      borderRadius: '20px',
      border: `1px solid ${theme.palette.divider}`,
      overflow: 'hidden',
      '@keyframes fadeInRight': { from: { opacity: 0, transform: 'translateX(16px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
      animation: 'fadeInRight 0.4s 0.15s ease forwards',
      opacity: 0,
    })}>
      {/* Header */}
      <Box sx={(theme) => ({
        p: 2.5,
        borderBottom: `1px solid ${theme.palette.divider}`,
        background: theme.palette.mode === 'dark'
          ? 'linear-gradient(135deg, rgba(124,58,237,0.08) 0%, rgba(37,99,235,0.04) 100%)'
          : 'linear-gradient(135deg, rgba(124,58,237,0.05) 0%, rgba(37,99,235,0.03) 100%)',
        flexShrink: 0,
      })}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ width: 38, height: 38, borderRadius: '11px', background: 'linear-gradient(135deg, #7C3AED, #2563EB)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(124,58,237,0.3)' }}>
            <ChatBubble sx={{ color: 'white', fontSize: 18 }} />
          </Box>
          <Box>
            <Typography variant="h6">Ask About Your Document</Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>Powered by Gemini AI</Typography>
          </Box>
        </Box>
      </Box>

      {/* Messages */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2, minHeight: 0 }}>
        {/* Empty state */}
        {qaHistory.length === 0 && !isLoading && (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, textAlign: 'center', py: 2 }}>
            <Box sx={{ width: 56, height: 56, borderRadius: '16px', mb: 2, bgcolor: 'rgba(124,58,237,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <SmartToy sx={{ fontSize: 30, color: 'primary.main', opacity: 0.7 }} />
            </Box>
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3, maxWidth: 260 }}>
              Ask me anything about your document — clauses, obligations, risks, and more.
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
              {SUGGESTED.slice(0, 4).map(q => (
                <Chip key={q} label={q} size="small" onClick={() => submit(q)} sx={{ cursor: 'pointer', bgcolor: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)', color: 'primary.main', '&:hover': { bgcolor: 'rgba(124,58,237,0.15)' }, transition: 'all 0.18s', fontSize: '0.78rem' }} />
              ))}
            </Box>
          </Box>
        )}

        {/* Conversation */}
        {qaHistory.map((qa, idx) => {
          const confColor = CONFIDENCE_COLORS[qa.confidence] ?? '#D97706';
          return (
            <Box key={idx} sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {/* User */}
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-end', gap: 1 }}>
                <Box sx={{ maxWidth: '82%', px: 2.5, py: 1.75, background: 'linear-gradient(135deg, #7C3AED, #2563EB)', borderRadius: '18px 18px 4px 18px', boxShadow: '0 4px 20px rgba(124,58,237,0.22)' }}>
                  <Typography variant="body2" sx={{ color: 'white', lineHeight: 1.65 }}>{qa.question}</Typography>
                </Box>
                <Box sx={{ width: 28, height: 28, flexShrink: 0, borderRadius: '50%', bgcolor: 'action.selected', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Person sx={{ fontSize: 15, color: 'text.secondary' }} />
                </Box>
              </Box>

              {/* AI */}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                <Box sx={{ width: 28, height: 28, flexShrink: 0, borderRadius: '50%', background: 'linear-gradient(135deg, #7C3AED, #2563EB)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <SmartToy sx={{ fontSize: 15, color: 'white' }} />
                </Box>
                <Box sx={(theme) => ({
                  maxWidth: '87%', px: 2, py: 1.75,
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: '4px 18px 18px 18px',
                })}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 700 }}>Legal EASE AI</Typography>
                    <Box sx={{ px: 0.75, py: 0.15, borderRadius: '5px', fontSize: '0.62rem', fontWeight: 800, color: confColor, bgcolor: `${confColor}18`, border: `1px solid ${confColor}30` }}>
                      {qa.confidence.toUpperCase()}
                    </Box>
                  </Box>
                  <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.75 }}>{qa.answer}</Typography>
                  {qa.source_section && (
                    <Box sx={{ mt: 1.5, px: 1.5, py: 1, bgcolor: 'rgba(124,58,237,0.07)', border: '1px solid rgba(124,58,237,0.15)', borderRadius: '8px' }}>
                      <Typography variant="caption" sx={{ color: 'primary.main', lineHeight: 1.5, display: 'block' }}>📄 {qa.source_section}</Typography>
                    </Box>
                  )}
                </Box>
              </Box>
            </Box>
          );
        })}

        {/* Typing */}
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <Box sx={{ width: 28, height: 28, flexShrink: 0, borderRadius: '50%', background: 'linear-gradient(135deg, #7C3AED, #2563EB)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <SmartToy sx={{ fontSize: 15, color: 'white' }} />
            </Box>
            <Box sx={(theme) => ({ px: 2, py: 1.5, bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)', border: `1px solid ${theme.palette.divider}`, borderRadius: '4px 18px 18px 18px' })}>
              <TypingIndicator />
            </Box>
          </Box>
        )}

        {/* Error */}
        {error && (
          <Box sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(220,38,38,0.07)', border: '1px solid rgba(220,38,38,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2" sx={{ color: 'error.main' }}>{error}</Typography>
            <Button size="small" sx={{ color: 'error.main', minWidth: 'auto', p: 0.5 }} onClick={() => setError(null)}>✕</Button>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Follow-up chips */}
      {qaHistory.length > 0 && !isLoading && unusedSuggestions.length > 0 && (
        <Box sx={(theme) => ({ px: 2, pb: 1.5, display: 'flex', flexWrap: 'wrap', gap: 0.75, flexShrink: 0, borderTop: `1px solid ${theme.palette.divider}`, pt: 1.5 })}>
          {unusedSuggestions.slice(0, 3).map(q => (
            <Chip key={q} label={q} size="small" onClick={() => submit(q)} sx={{ cursor: 'pointer', bgcolor: 'rgba(124,58,237,0.07)', border: '1px solid rgba(124,58,237,0.18)', color: 'primary.main', '&:hover': { bgcolor: 'rgba(124,58,237,0.14)' }, fontSize: '0.72rem', transition: 'all 0.18s' }} />
          ))}
        </Box>
      )}

      {/* Input */}
      <Box component="form" onSubmit={handleSubmit} sx={(theme) => ({ p: 2, borderTop: `1px solid ${theme.palette.divider}`, display: 'flex', gap: 1.25, flexShrink: 0, bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.15)' : 'rgba(0,0,0,0.02)' })}>
        <TextField
          inputRef={inputRef}
          fullWidth size="small"
          placeholder="Ask a question about your document..."
          value={question}
          onChange={e => { setQuestion(e.target.value); if (error) setError(null); }}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          multiline maxRows={4}
          sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontSize: '0.875rem' } }}
        />
        <Button type="submit" variant="contained" disabled={!question.trim() || isLoading}
          sx={{ minWidth: 44, px: 1.5, borderRadius: '12px', alignSelf: 'flex-end', height: 40 }}>
          {isLoading ? <CircularProgress size={16} color="inherit" /> : <Send sx={{ fontSize: 18 }} />}
        </Button>
      </Box>
    </Box>
  );
};

export default QAInterface;
