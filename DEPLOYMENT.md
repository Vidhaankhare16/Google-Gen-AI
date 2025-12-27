# Lexi Simplify - Deployment Guide

This guide will help you deploy the Lexi Simplify legal document AI platform to Google Cloud Run.

## Prerequisites

- Google Cloud Platform account
- Google Cloud CLI (`gcloud`) installed and configured
- Docker installed locally
- Node.js 18+ and Python 3.11+ for local development

## Quick Deployment

### 1. Google Cloud Setup

```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Run the GCP setup script
chmod +x setup-gcp.sh
./setup-gcp.sh
```

This script will:
- Enable required APIs (Vertex AI, Cloud Run, Cloud Build)
- Create a service account with proper permissions
- Generate a service account key

### 2. Configure Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit the .env file with your settings
nano backend/.env
```

Required environment variables:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
GEMINI_API_KEY=your-gemini-api-key  # Optional, can use Vertex AI instead
FLASK_ENV=production
MAX_FILE_SIZE=10485760
PORT=8080
```

### 3. Deploy to Google Cloud Run

```bash
# Make deployment script executable
chmod +x deploy.sh

# Deploy to Google Cloud Run
./deploy.sh
```

The deployment script will:
- Build the Docker container
- Push to Google Container Registry
- Deploy to Cloud Run with proper configuration
- Set up environment variables and scaling

### 4. Verify Deployment

After deployment, test your application:

```bash
# Get the service URL
gcloud run services describe lexi-simplify --region=us-central1 --format="value(status.url)"

# Test health endpoint
curl https://your-service-url/api/health
```

## Local Development

### 1. Install Dependencies

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Run Locally

```bash
# Option 1: Using Docker Compose (Recommended)
docker-compose up --build

# Option 2: Run services separately
# Terminal 1 - Backend
cd backend
python app.py

# Terminal 2 - Frontend
cd frontend
npm start
```

### 3. Test Locally

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Health Check: http://localhost:5000/api/health

## Configuration Options

### Google Cloud AI

You can use either:

1. **Vertex AI** (Recommended for production):
   - Set `GOOGLE_CLOUD_PROJECT` and `VERTEX_AI_LOCATION`
   - Uses service account authentication

2. **Gemini API** (Easier for development):
   - Set `GEMINI_API_KEY`
   - Direct API access

### Scaling Configuration

The Cloud Run service is configured with:
- **CPU**: 1 vCPU
- **Memory**: 2GB
- **Concurrency**: 10 requests per instance
- **Auto-scaling**: 0 to 10 instances
- **Timeout**: 300 seconds

Modify `cloud-run-service.yaml` to adjust these settings.

### Security Features

- HTTPS enforcement
- CORS configuration
- Rate limiting (5 uploads per 5 minutes, 20 questions per 5 minutes)
- File validation and sanitization
- Automatic document cleanup

## Monitoring

### Health Checks

- **Endpoint**: `/api/health`
- **Google Cloud**: Automatic health checks configured
- **Monitoring**: Built-in performance metrics

### Logs

```bash
# View application logs
gcloud logs read --service=lexi-simplify --limit=50

# Stream logs in real-time
gcloud logs tail --service=lexi-simplify
```

### Metrics

Access metrics at `/api/health` or through Google Cloud Monitoring:
- Request count and success rate
- Response times
- System resource usage
- Document processing statistics

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   # Verify service account key
   gcloud auth application-default login
   ```

2. **API Quota Exceeded**:
   - Check Google Cloud Console for API quotas
   - Consider upgrading to paid tier

3. **Memory Issues**:
   - Increase Cloud Run memory allocation
   - Optimize PDF processing for large files

4. **Build Failures**:
   ```bash
   # Check deployment readiness
   python check-deployment.py
   
   # Test Docker build locally
   docker build -t lexi-simplify .
   ```

### Debug Mode

For development debugging:

```bash
# Set debug environment
export FLASK_ENV=development

# Enable verbose logging
export FLASK_DEBUG=1
```

## Cost Optimization

- **Cloud Run**: Pay only for requests (scales to zero)
- **Vertex AI**: Pay per API call
- **Storage**: Temporary in-memory storage (no persistent costs)

Estimated costs for moderate usage:
- Cloud Run: $5-20/month
- Vertex AI: $10-50/month depending on usage
- Total: ~$15-70/month

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **Service Account**: Use minimal required permissions
3. **HTTPS**: Always enabled in production
4. **Rate Limiting**: Configured to prevent abuse
5. **Input Validation**: All user inputs are validated and sanitized

## Support

For issues or questions:
1. Check the logs: `gcloud logs read --service=lexi-simplify`
2. Verify configuration: `python check-deployment.py`
3. Test locally: `docker-compose up --build`

## Next Steps

After successful deployment:
1. Set up custom domain (optional)
2. Configure monitoring alerts
3. Implement user authentication (for production)
4. Add document persistence (for production)
5. Scale based on usage patterns