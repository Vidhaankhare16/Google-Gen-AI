# WhatsApp Demo Setup Guide for Legal EASE

This guide will help you set up the WhatsApp integration for Legal EASE, allowing users to upload PDFs and get AI analysis directly through WhatsApp.

## Prerequisites

1. **Twilio Account** (for WhatsApp Business API)
2. **WhatsApp Business Account** (optional, for production)
3. **Deployed Legal EASE Backend** (Google Cloud Run)

## Step 1: Set up Twilio WhatsApp Sandbox (Free Demo)

### 1.1 Create Twilio Account
1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up for a free account
3. Verify your phone number

### 1.2 Access WhatsApp Sandbox
1. In Twilio Console, go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Note your **Sandbox WhatsApp Number** (e.g., +1 415 523 8886)
3. Note the **Join Code** (e.g., "join legal-ease-demo")

### 1.3 Get Twilio Credentials
1. From Twilio Console Dashboard, copy:
   - **Account SID**
   - **Auth Token**
2. Keep these secure - you'll need them for deployment

## Step 2: Configure Webhook

### 2.1 Set Webhook URL
1. In Twilio Console, go to **Messaging** → **Settings** → **WhatsApp sandbox settings**
2. Set **Webhook URL** to: `https://your-app-url.run.app/whatsapp/webhook`
3. Set **HTTP Method** to: `POST`
4. Save configuration

### 2.2 Test Webhook
```bash
# Test webhook endpoint
curl -X GET https://your-app-url.run.app/whatsapp/webhook
# Should return: "WhatsApp webhook verified"
```

## Step 3: Deploy with WhatsApp Support

### 3.1 Update Environment Variables
```bash
# Deploy with WhatsApp credentials
gcloud run deploy lexi-simplify \
  --source . \
  --region us-central1 \
  --set-env-vars "GEMINI_API_KEY=your-gemini-key,GOOGLE_CLOUD_PROJECT=your-project,VERTEX_AI_LOCATION=us-central1,FLASK_ENV=production,MAX_FILE_SIZE=10485760,SESSION_TIMEOUT=3600,TWILIO_ACCOUNT_SID=your-account-sid,TWILIO_AUTH_TOKEN=your-auth-token,TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886"
```

### 3.2 Verify Deployment
```bash
# Check health
curl https://your-app-url.run.app/api/health

# Check WhatsApp webhook
curl https://your-app-url.run.app/whatsapp/webhook
```

## Step 4: Test WhatsApp Demo

### 4.1 Join Sandbox
1. Send WhatsApp message to **+1 (415) 523-8886**
2. Send the join code: `join legal-ease-demo`
3. You should receive a confirmation message

### 4.2 Test Document Analysis
1. **Send a PDF**: Upload any legal document (rental agreement, contract, etc.)
2. **Get Analysis**: Receive AI-powered analysis with:
   - Document summary
   - Key points
   - Important warnings
   - Suggested questions

### 4.3 Test Q&A Feature
1. **Ask Questions**: After uploading a document, ask questions like:
   - "What is the monthly rent?"
   - "Can I have pets?"
   - "What are the termination conditions?"
   - "Are there any concerning clauses?"
2. **Get Answers**: Receive AI-powered responses with source references

## Step 5: Demo Commands

Users can send these commands in WhatsApp:

| Command | Description |
|---------|-------------|
| `help` | Show help message with instructions |
| `start` | Show welcome message |
| `new` | Clear session and start fresh |
| Send PDF | Analyze legal document |
| Ask question | Get answers about uploaded document |

## Step 6: Production Setup (Optional)

For production use with your own WhatsApp Business number:

### 6.1 WhatsApp Business API
1. Apply for **WhatsApp Business API** access
2. Get approved by Meta/WhatsApp
3. Configure your business profile

### 6.2 Custom Phone Number
1. Purchase a phone number from Twilio
2. Configure WhatsApp for that number
3. Update `TWILIO_WHATSAPP_NUMBER` environment variable

## Example User Flow

```
User: [Sends PDF rental agreement]

Legal EASE: 📄 *Analyzing your document...* 
This may take a few moments. I'll send you the results shortly! ⏳

Legal EASE: 📄 *Document Analysis: your document*

📋 *SUMMARY*
This rental agreement outlines the terms between landlord and tenant for a 12-month lease starting January 1, 2024, with monthly rent of $1,200...

✅ *KEY POINTS*
1. Monthly rent: $1,200 due on the 1st of each month
2. Security deposit: $2,400 (two months rent)
3. Late fee: $50 if rent is paid after the 5th
4. Lease term: 12 months starting January 1, 2024
5. Tenant responsible for utilities except water and trash

⚠️ *IMPORTANT WARNINGS*
1. No pets allowed without written permission
2. 30-day notice required for termination
3. Maximum occupancy limited to 2 people

💬 *Ask me questions about this document!*

User: What happens if I pay rent late?

Legal EASE: ❓ *Your Question:*
What happens if I pay rent late?

🤖 *Legal EASE AI Answer:*
If you pay rent after the 5th of the month, you will be charged a late fee of $50 according to the lease terms.

📄 *Source Reference:*
Late fee: $50 if rent is paid after the 5th

🎯 *Confidence: High*

💡 *Ask another question or send a new document to analyze!*
```

## Troubleshooting

### Common Issues

1. **Webhook not receiving messages**
   - Check webhook URL is correct
   - Ensure HTTPS is enabled
   - Verify Twilio credentials

2. **PDF processing fails**
   - Ensure PDF contains readable text
   - Check file size (under 10MB)
   - Verify PDF is not password protected

3. **AI analysis not working**
   - Check Gemini API key is valid
   - Verify environment variables are set
   - Check application logs

### Debug Commands

```bash
# Check logs
gcloud run services logs read lexi-simplify --region=us-central1 --limit=50

# Test API endpoints
curl -X POST https://your-app-url.run.app/whatsapp/webhook \
  -d "From=whatsapp:+1234567890" \
  -d "Body=help"
```

## Security Considerations

1. **Webhook Security**: Implement Twilio signature validation
2. **Rate Limiting**: Already implemented (50 requests per 5 minutes)
3. **Data Privacy**: Documents are temporarily stored and auto-deleted
4. **User Sessions**: Stored in memory, cleared automatically

## Cost Estimation

**Twilio Sandbox (Free Demo):**
- Free for testing
- Limited to pre-approved numbers

**Production Costs:**
- WhatsApp messages: ~$0.005 per message
- Twilio phone number: ~$1/month
- Google Cloud Run: Pay per use
- Gemini API: Pay per request

**Estimated monthly cost for 1000 users:**
- WhatsApp: ~$25-50
- Cloud Run: ~$10-20
- Gemini API: ~$30-60
- **Total: ~$65-130/month**

Your WhatsApp demo is now ready! Users can upload legal documents and get AI analysis directly through WhatsApp. 🎉