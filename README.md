# Create.ai - AI-Powered Content Creation Platform

An emergency sprint build designed to generate $20M in revenue within 23 hours through viral AI-powered content creation.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)
- PostgreSQL 16
- Redis 7

### Environment Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/create-ai.git
cd create-ai
```

2. Copy environment files
```bash
cp backend/.env.example backend/.env
```

3. Update the `.env` file with your API keys:
- AI Model API keys (Whisper, QwQ, Llama, FLUX, MeloTTS)
- Stripe API keys
- AWS S3 credentials
- Sentry DSN (optional)
- Mixpanel token (optional)

### 🐳 Docker Deployment (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 💻 Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Start Required Services
```bash
# PostgreSQL
docker run -d --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16

# Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Celery Worker (in backend directory)
celery -A app.celery_app worker --loglevel=info

# Celery Beat (in another terminal)
celery -A app.celery_app beat --loglevel=info
```

## 🏗️ Architecture

### Tech Stack
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Framer Motion
- **Backend**: FastAPI, Python 3.11, Celery, Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Storage**: AWS S3 with CloudFront CDN
- **AI Models**: 
  - Whisper Large v3 Turbo (speech-to-text)
  - QwQ-32B (reasoning)
  - Llama 4 Scout 17B (content generation)
  - FLUX.1 Schnell (image generation)
  - MeloTTS (text-to-speech)
  - Llama 3.2 11B Vision (quality checking)

### Key Features
- ⚡ Sub-30 second content creation pipeline
- 💰 Dynamic surge pricing based on server load
- 🏆 Viral challenge system with leaderboards
- 🔄 Platform-specific sharing (TikTok, Instagram, Twitter, YouTube)
- 💳 Stripe payment integration
- 📊 Real-time analytics dashboard
- 🚀 Auto-scaling with connection pooling
- 🛡️ Rate limiting and DDoS protection

## 📊 Monitoring

### Metrics Endpoint
- Backend metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090 (if configured)

### Key Metrics to Track
- Creation success rate
- Average processing time
- Revenue per hour
- Viral coefficient
- Server load percentage
- API response times

## 🚨 Production Checklist

- [ ] Set all environment variables
- [ ] Configure SSL certificates
- [ ] Set up CloudFlare DDoS protection
- [ ] Configure auto-scaling groups
- [ ] Set up database backups
- [ ] Configure Sentry error tracking
- [ ] Set up Mixpanel analytics
- [ ] Test payment flows
- [ ] Load test with expected traffic
- [ ] Set up monitoring alerts

## 📈 Revenue Optimization

### Surge Pricing Triggers
- CPU usage > 80%
- Memory usage > 80%
- Active users > 10,000

### Viral Mechanics
1. Launch with 5 template challenges
2. Influencer seeding (first 100 users)
3. Referral rewards (1 free creation per 3 referrals)
4. Platform-optimized sharing
5. Real-time leaderboards

## 🛠️ Troubleshooting

### Common Issues

**Creation failures**
- Check AI API keys and endpoints
- Verify Redis is running
- Check Celery worker logs

**Slow processing**
- Monitor AI model latencies
- Check database connection pool
- Verify S3 upload speeds

**Payment issues**
- Verify Stripe webhook configuration
- Check webhook secret is correct
- Monitor Stripe dashboard

## 📝 API Documentation

Interactive API docs available at: http://localhost:8000/docs

Key endpoints:
- POST `/api/auth/register` - User registration
- POST `/api/creations/create` - Create content
- GET `/api/challenges/trending` - Get trending challenges
- POST `/api/payments/purchase` - Process payment

## 🚀 Scaling Notes

The system is designed to handle:
- 10M+ concurrent users
- 100K+ creations per minute
- Auto-scaling based on load
- Fallback AI endpoints
- Smart caching with Redis

## 📄 License

Proprietary - Built for the $20M Sprint Challenge

---

**Success Metric**: $20M revenue in 23 hours 🎯