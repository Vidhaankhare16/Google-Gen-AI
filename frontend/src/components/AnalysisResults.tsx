import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as NewDocIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

import { AnalysisResult } from '../types/api';
import ApiService from '../services/api';

const SummaryCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  backgroundColor: theme.palette.primary.light,
  color: theme.palette.primary.contrastText,
}));

const KeyPointsCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
}));

const WarningsCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  borderLeft: `4px solid ${theme.palette.warning.main}`,
}));

const SectionHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: theme.spacing(2),
}));

interface AnalysisResultsProps {
  result: AnalysisResult;
  onNewDocument: () => void;
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  result,
  onNewDocument,
}) => {
  const [expandedSections, setExpandedSections] = useState({
    keyPoints: true,
    warnings: true,
  });
  const [isDeleting, setIsDeleting] = useState(false);

  const toggleSection = (section: 'keyPoints' | 'warnings') => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleDeleteDocument = async () => {
    if (!result.document_id) return;

    setIsDeleting(true);
    try {
      await ApiService.deleteDocument(result.document_id);
      onNewDocument(); // This will reset the UI to upload state
    } catch (error: any) {
      console.error('Failed to delete document:', error.message);
      // Continue to new document even if deletion fails
      onNewDocument();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" component="h2">
          Document Analysis Results
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<DeleteIcon />}
            onClick={handleDeleteDocument}
            disabled={isDeleting}
            size="small"
          >
            {isDeleting ? 'Deleting...' : 'Delete Document'}
          </Button>
          <Button
            variant="contained"
            startIcon={<NewDocIcon />}
            onClick={onNewDocument}
            size="small"
          >
            Analyze New Document
          </Button>
        </Box>
      </Box>

      {/* Summary Section */}
      <SummaryCard elevation={3}>
        <CardContent>
          <SectionHeader>
            <InfoIcon sx={{ mr: 1 }} />
            <Typography variant="h6" component="h3">
              Key Takeaways
            </Typography>
          </SectionHeader>
          <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
            {result.summary || 'No summary available.'}
          </Typography>
        </CardContent>
      </SummaryCard>

      {/* Key Points Section */}
      <KeyPointsCard elevation={2}>
        <CardContent>
          <SectionHeader>
            <CheckIcon sx={{ mr: 1, color: 'success.main' }} />
            <Typography variant="h6" component="h3" sx={{ flexGrow: 1 }}>
              Important Clauses ({result.key_points?.length || 0})
            </Typography>
            <IconButton
              onClick={() => toggleSection('keyPoints')}
              size="small"
            >
              {expandedSections.keyPoints ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </SectionHeader>

          <Collapse in={expandedSections.keyPoints}>
            {result.key_points && result.key_points.length > 0 ? (
              <List>
                {result.key_points.map((point, index) => (
                  <ListItem key={index} alignItems="flex-start">
                    <ListItemIcon>
                      <Chip
                        label={index + 1}
                        size="small"
                        color="primary"
                        sx={{ minWidth: 32 }}
                      />
                    </ListItemIcon>
                    <ListItemText
                      primary={point}
                      primaryTypographyProps={{
                        variant: 'body1',
                        sx: { lineHeight: 1.5 }
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No key points identified in this document.
              </Typography>
            )}
          </Collapse>
        </CardContent>
      </KeyPointsCard>

      {/* Warnings Section */}
      {result.warnings && result.warnings.length > 0 && (
        <WarningsCard elevation={2}>
          <CardContent>
            <SectionHeader>
              <WarningIcon sx={{ mr: 1, color: 'warning.main' }} />
              <Typography variant="h6" component="h3" sx={{ flexGrow: 1 }}>
                Potential Concerns ({result.warnings.length})
              </Typography>
              <IconButton
                onClick={() => toggleSection('warnings')}
                size="small"
              >
                {expandedSections.warnings ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </SectionHeader>

            <Collapse in={expandedSections.warnings}>
              <List>
                {result.warnings.map((warning, index) => (
                  <ListItem key={index} alignItems="flex-start">
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary={warning}
                      primaryTypographyProps={{
                        variant: 'body1',
                        sx: { lineHeight: 1.5 }
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </WarningsCard>
      )}

      <Divider sx={{ my: 3 }} />

      {/* Footer Information */}
      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="body2">
          <strong>Next Steps:</strong> Use the Q&A section below to ask specific questions about clauses, 
          terms, or obligations in your document. You can also analyze a new document using the button above.
        </Typography>
      </Alert>

      <Alert severity="warning" sx={{ mt: 1 }}>
        <Typography variant="body2">
          <strong>Important:</strong> This analysis is for informational purposes only and does not constitute 
          legal advice. Always consult with a qualified attorney for legal matters.
        </Typography>
      </Alert>
    </Box>
  );
};

export default AnalysisResults;