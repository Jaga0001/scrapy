# AI Web Scraper Deployment Guide

This guide covers multiple deployment options for the AI Web Scraper application.

## Prerequisites

- Python 3.8+
- Git
- Domain name (for production deployments)
- SSL certificate (recommended for production)

## Local Development Deployment

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd ai-web-scraper
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run the Application
```bash
python run.py
# Choose option 3 to start both API and dashboard
```

## Docker Deployment

### 1. Build Docker Image
```bash
docker build -t ai-web-scraper .
```

### 2. Run with Docker Compose
```bash
docker-compose up -d
```

### 3. Access the Application
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/docs

## Cloud Deployment Options

### Option 1: Railway (Recommended for beginners)

1. **Prepare your repository**
   - Ensure all files are committed to Git
   - Push to GitHub/GitLab

2. **Deploy to Railway**
   - Go to [railway.app](https://railway.app)
   - Connect your GitHub account
   - Select your repository
   - Railway will auto-detect Python and deploy

3. **Environment Variables**
   Set these in Railway dashboard:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=sqlite:///./webscraper.db
   API_HOST=0.0.0.0
   API_PORT=8000
   DASHBOARD_HOST=0.0.0.0
   DASHBOARD_PORT=8501
   ```

### Option 2: Heroku

1. **Install Heroku CLI**
   ```bash
   # Install from https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Create Heroku Apps**
   ```bash
   heroku create your-app-api
   heroku create your-app-dashboard
   ```

3. **Deploy API**
   ```bash
   git subtree push --prefix=src/api heroku main
   ```

4. **Deploy Dashboard**
   ```bash
   git subtree push --prefix=src/dashboard heroku main
   ```

### Option 3: DigitalOcean App Platform

1. **Create App**
   - Go to DigitalOcean App Platform
   - Connect your GitHub repository

2. **Configure Services**
   - API Service: `python src/api/main.py`
   - Dashboard Service: `streamlit run src/dashboard/main.py`

3. **Set Environment Variables**
   ```
   GEMINI_API_KEY=your_api_key
   DATABASE_URL=your_database_url
   ```

### Option 4: AWS (Advanced)

1. **API Deployment (AWS Lambda + API Gateway)**
   ```bash
   # Install AWS CLI and configure
   pip install awscli
   aws configure
   
   # Deploy using AWS SAM or Serverless Framework
   ```

2. **Dashboard Deployment (AWS ECS or EC2)**
   ```bash
   # Use ECS for containerized deployment
   # Or EC2 for traditional server deployment
   ```

## Production Configuration

### 1. Environment Variables
```bash
# Production .env
ENVIRONMENT=production
DEBUG=false
GEMINI_API_KEY=your_production_api_key
DATABASE_URL=postgresql://user:pass@host:port/db
API_HOST=0.0.0.0
API_PORT=8000
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501
CORS_ORIGINS=https://yourdomain.com,https://dashboard.yourdomain.com
```

### 2. Database Setup
```bash
# For PostgreSQL (recommended for production)
pip install psycopg2-binary
# Update DATABASE_URL in .env
```

### 3. SSL/HTTPS Setup
```bash
# Use a reverse proxy like Nginx
# Or configure SSL in your cloud provider
```

### 4. Process Management
```bash
# Use PM2 for process management
npm install -g pm2
pm2 start ecosystem.config.js
```

## Monitoring and Maintenance

### 1. Health Checks
- API Health: `GET /api/v1/health`
- Dashboard: Check if Streamlit is responding

### 2. Logging
```bash
# Check logs
tail -f logs/app.log
```

### 3. Database Backup
```bash
# SQLite backup
cp webscraper.db webscraper_backup_$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 4. Updates
```bash
git pull origin main
pip install -r requirements.txt
# Restart services
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill process using port
   lsof -ti:8000 | xargs kill -9
   ```

2. **Database Connection Issues**
   ```bash
   # Check database URL and permissions
   # Ensure database server is running
   ```

3. **API Not Responding**
   ```bash
   # Check if API server is running
   curl http://localhost:8000/api/v1/health
   ```

4. **Dashboard Not Loading**
   ```bash
   # Check Streamlit logs
   streamlit run src/dashboard/main.py --logger.level debug
   ```

### Performance Optimization

1. **Database Optimization**
   - Add indexes for frequently queried fields
   - Use connection pooling
   - Regular database maintenance

2. **API Optimization**
   - Enable caching
   - Use async operations
   - Implement rate limiting

3. **Dashboard Optimization**
   - Cache API responses
   - Optimize data loading
   - Use pagination for large datasets

## Security Considerations

1. **API Security**
   - Use HTTPS in production
   - Implement authentication
   - Validate all inputs
   - Use rate limiting

2. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Regular security updates

3. **Environment Security**
   - Never commit secrets to Git
   - Use environment variables
   - Regular security audits

## Scaling

### Horizontal Scaling
- Use load balancers
- Deploy multiple API instances
- Use database clustering

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Use caching layers

## Support

For deployment issues:
1. Check the logs first
2. Verify environment variables
3. Test API endpoints manually
4. Check database connectivity
5. Review security settings

## Quick Deploy Commands

### Railway
```bash
# One-command deploy
railway login
railway link
railway up
```

### Docker
```bash
# Quick Docker deployment
docker-compose up -d
```

### Local Production
```bash
# Production-like local deployment
python run.py
```