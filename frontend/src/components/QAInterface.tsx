import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Chip,
  Alert,
  Divider,
} from '@mui/material';
import {
  Send as SendIcon,
  QuestionAnswer as QAIcon,
  Person as UserIcon,
  SmartToy as AIIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

import ApiService from '../services/api';
import { QuestionAnswer } from '../types/api';

const QAContainer = styled(Box)(({ theme }) => ({
  maxHeight: '500px',
  overflowY: 'auto',
  padding: theme.spacing(1),
  '&::-webkit-scrollbar': {
    width: '8px',
  },
  '&::-webkit-scrollbar-track': {
    background: theme.palette.grey[100],
    borderRadius: '4px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.grey[400],
    borderRadius: '4px',
  },
}));

const MessageBubble = styled(Paper)<{ isUser?: boolean }>(({ theme, isUser }) => ({
  padding: theme.spacing(2.5),
  marginBottom: theme.spacing(2),
  maxWidth: '85%',
  alignSelf: isUser ? 'flex-end' : 'flex-start',
  backgroundColor: isUser ? '#1976d2' : '#f8f9fa',
  color: isUser ? '#ffffff' : theme.palette.text.primary,
  borderRadius: theme.spacing(2.5),
  borderBottomRightRadius: isUser ? theme.spacing(0.5) : theme.spacing(2.5),
  borderBottomLeftRadius: isUser ? theme.spacing(2.5) : theme.spacing(0.5),
  boxShadow: isUser ? '0 2px 12px rgba(25, 118, 210, 0.15)' : '0 2px 8px rgba(0,0,0,0.08)',
  border: isUser ? 'none' : '1px solid #e0e0e0',
}));

const MessageContainer = styled(Box)({
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
});

const ConfidenceChip = styled(Chip)<{ confidence: string }>(({ theme, confidence }) => ({
  marginTop: theme.spacing(1),
  backgroundColor: 
    confidence === 'high' ? theme.palette.success.light :
    confidence === 'medium' ? theme.palette.warning.light :
    theme.palette.error.light,
  color: 
    confidence === 'high' ? theme.palette.success.contrastText :
    confidence === 'medium' ? theme.palette.warning.contrastText :
    theme.palette.error.contrastText,
}));

interface QAInterfaceProps {
  documentId: string;
}

const QAInterface: React.FC<QAInterfaceProps> = ({ documentId }) => {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [qaHistory, setQAHistory] = useState<QuestionAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [qaHistory]);

  const handleSubmitQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim() || isLoading) return;

    const currentQuestion = question.trim();
    setQuestion('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await ApiService.askQuestion(documentId, currentQuestion);

      if (response.success && response.answer) {
        const newQA: QuestionAnswer = {
          question: currentQuestion,
          answer: response.answer,
          source_section: response.source_section,
          confidence: response.confidence || 'medium',
          document_id: documentId,
          answered_at: response.answered_at || new Date().toISOString(),
        };

        setQAHistory(prev => [...prev, newQA]);

        if (response.warning) {
          setError(response.warning);
        }
      } else {
        throw new Error('Failed to get answer');
      }
    } catch (error: any) {
      setError(error.message || 'Failed to answer question');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuestionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuestion(e.target.value);
    if (error) setError(null); // Clear error when user starts typing
  };

  const suggestedQuestions = [
    "What are the key obligations in this document?",
    "What are the payment terms?",
    "What happens if I terminate early?",
    "Are there any penalties or fees?",
    "What are my rights under this agreement?",
  ];

  const handleSuggestedQuestion = (suggestedQ: string) => {
    if (!isLoading) {
      setQuestion(suggestedQ);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            backgroundColor: '#e3f2fd',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mr: 2,
          }}
        >
          <QAIcon sx={{ color: '#1976d2', fontSize: 20 }} />
        </Box>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
            Ask Questions About Your Document
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Get instant answers about specific clauses, terms, and conditions
          </Typography>
        </Box>
      </Box>

      {qaHistory.length === 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Try asking questions like:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {suggestedQuestions.map((suggestedQ, index) => (
              <Chip
                key={index}
                label={suggestedQ}
                variant="outlined"
                size="small"
                onClick={() => handleSuggestedQuestion(suggestedQ)}
                sx={{ cursor: 'pointer' }}
                disabled={isLoading}
              />
            ))}
          </Box>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <QAContainer>
        <MessageContainer>
          {qaHistory.map((qa, index) => (
            <React.Fragment key={index}>
              {/* User Question */}
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-start' }}>
                <MessageBubble isUser elevation={0}>
                  <Typography variant="body1" sx={{ lineHeight: 1.5 }}>
                    {qa.question}
                  </Typography>
                </MessageBubble>
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    backgroundColor: '#e0e0e0',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    ml: 2,
                    mt: 0.5,
                    flexShrink: 0,
                  }}
                >
                  <UserIcon sx={{ color: '#666', fontSize: 18 }} />
                </Box>
              </Box>

              {/* AI Answer */}
              <Box sx={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'flex-start' }}>
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    backgroundColor: '#1976d2',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    mr: 2,
                    mt: 0.5,
                    flexShrink: 0,
                  }}
                >
                  <AIIcon sx={{ color: 'white', fontSize: 18 }} />
                </Box>
                <MessageBubble elevation={0}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                    <Typography variant="body2" fontWeight="600" sx={{ color: '#1976d2' }}>
                      Legal EASE AI
                    </Typography>
                    <ConfidenceChip
                      confidence={qa.confidence}
                      label={qa.confidence}
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  </Box>
                  <Typography variant="body1" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                    {qa.answer}
                  </Typography>
                  
                  {qa.source_section && (
                    <Box
                      sx={{
                        backgroundColor: '#f0f7ff',
                        border: '1px solid #e3f2fd',
                        borderRadius: 1,
                        p: 1.5,
                        mt: 1,
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 500, color: '#1976d2' }}>
                        📄 Source Reference:
                      </Typography>
                      <Typography variant="caption" display="block" sx={{ mt: 0.5, color: 'text.secondary' }}>
                        {qa.source_section}
                      </Typography>
                    </Box>
                  )}
                </MessageBubble>
              </Box>

              {index < qaHistory.length - 1 && <Divider sx={{ my: 2 }} />}
            </React.Fragment>
          ))}

          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
              <MessageBubble elevation={2}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CircularProgress size={20} sx={{ mr: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    Analyzing your question...
                  </Typography>
                </Box>
              </MessageBubble>
            </Box>
          )}
        </MessageContainer>
        <div ref={messagesEndRef} />
      </QAContainer>

      <Box component="form" onSubmit={handleSubmitQuestion} sx={{ mt: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Ask a question about your document..."
            value={question}
            onChange={handleQuestionChange}
            disabled={isLoading}
            multiline
            maxRows={3}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={!question.trim() || isLoading}
            sx={{
              minWidth: 56,
              height: 56,
              borderRadius: 2,
            }}
          >
            {isLoading ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              <SendIcon />
            )}
          </Button>
        </Box>
        
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Ask specific questions about clauses, terms, obligations, or any part of your document.
        </Typography>
      </Box>
    </Box>
  );
};

export default QAInterface;