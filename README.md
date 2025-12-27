# Legal EASE - AI-Powered Legal Document Analysis

Transform complex legal documents into clear, actionable guidance with AI. Legal EASE helps you understand rental agreements, contracts, and terms of service before you sign.

## 🚀 Features

- **📄 PDF Document Analysis**: Upload legal documents and get instant AI-powered analysis
- **🤖 Interactive Q&A**: Ask questions about specific clauses and get detailed answers
- **📱 WhatsApp Integration**: Analyze documents directly through WhatsApp
- **⚠️ Risk Detection**: Identify concerning clauses and potential issues
- **🔒 Secure Processing**: Documents are processed securely and automatically deleted
- **🌐 Web Interface**: Clean, user-friendly web application

## 🛠️ Technology Stack

- **Backend**: Python Flask, Google Gemini AI, Vertex AI
- **Frontend**: React, TypeScript, Material-UI
- **Document Processing**: PyPDF2, pdfplumber
- **WhatsApp**: Twilio WhatsApp Business API
- **Deployment**: Google Cloud Run, Docker
- **Security**: Rate limiting, input validation, secure headers

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- Google Cloud Project with Vertex AI enabled
- Gemini API key
- Twilio account (optional, for WhatsApp demo)

## 🔧 Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/legal-ease.git
cd legal-ease
```

### 2. Environment Setup
```bash
# Run the setup script
./setup-env.sh

# Edit backend/.env with your actual credentials
nano backend/.env
```

### 3. Required Environment Variables

Create `backend/.env` with:
```env
# Google Cloud & AI (Required)
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1

# Flask Configuration
FLASK_ENV=development
PORT=8080

# WhatsApp Integration (Optional)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### 4. Install Dependencies

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## 🚀 Running Locally

### Development Mode
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python app.py

# Terminal 2: Frontend
cd frontend
npm start
```

### Production Mode (Docker)
```bash
docker-compose up --build
```

## 🌐 Deployment

### Google Cloud Run
```bash
# Set environment variables
export GEMINI_API_KEY=your-gemini-api-key
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export TWILIO_ACCOUNT_SID=your-twilio-sid
export TWILIO_AUTH_TOKEN=your-twilio-token

# Deploy
./deploy-local-test.sh
```

### Manual Deployment
```bash
gcloud run deploy lexi-simplify \
  --source . \
  --region us-central1 \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
```

## 📱 WhatsApp Demo Setup

1. **Get Twilio Account**: Sign up at [Twilio Console](https://console.twilio.com/)
2. **Access WhatsApp Sandbox**: Go to Messaging → Try it out → Send a WhatsApp message
3. **Configure Webhook**: Set webhook URL to `https://your-app-url/whatsapp/webhook`
4. **Test**: Send "join your-code" to the Twilio WhatsApp number

See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) for detailed instructions.

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest

# API tests
python test_api.py

# WhatsApp integration tests
export APP_URL=https://your-deployed-url
python test_whatsapp.py
```

## 📖 API Documentation

### Analyze Document
```bash
POST /api/analyze
Content-Type: multipart/form-data

# Upload PDF file
curl -X POST -F "file=@document.pdf" https://your-app-url/api/analyze
```

### Ask Question
```bash
POST /api/question
Content-Type: application/json

{
  "question": "What is the monthly rent?",
  "document_id": "doc-id-from-analysis"
}
```

### WhatsApp Webhook
```bash
POST /whatsapp/webhook
# Handles incoming WhatsApp messages from Twilio
```

## 🔒 Security Features

- **Rate Limiting**: Prevents API abuse
- **Input Validation**: Validates all user inputs
- **Secure Headers**: CORS, CSP, and security headers
- **File Validation**: Ensures only valid PDFs are processed
- **Auto-cleanup**: Documents automatically deleted after processing
- **Environment Variables**: No hardcoded secrets

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web     │    │   WhatsApp      │    │   Python Flask  │
│   Frontend      │◄──►│   Integration   │◄──►│   Backend       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   Google        │
                                               │   Gemini AI     │
                                               └─────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Commit changes: `git commit -am 'Add feature'`
6. Push to branch: `git push origin feature-name`
7. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guide
- **WhatsApp Setup**: See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md)
- **Issues**: Create an issue on GitHub
- **Email**: support@legal-ease.com

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Document comparison features
- [ ] Legal template library
- [ ] Advanced analytics dashboard
- [ ] Mobile app (iOS/Android)
- [ ] Enterprise features

## ⭐ Star History

If you find this project helpful, please consider giving it a star on GitHub!

---

**Legal EASE** - Making legal documents accessible to everyone 📚✨