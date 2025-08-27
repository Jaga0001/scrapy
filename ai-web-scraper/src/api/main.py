"""
FastAPI application for AI-powered web scraping API.
"""

import sys
import os
from uuid import uuid4

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import time
import google.generativeai as genai

from src.database import get_db
from src.models.database_models import ScrapingJobORM, ScrapedDataORM
from src.models.pydantic_models import (
    ScrapingJob, ScrapedData, JobStatus, ScrapingConfig,
    JobResponse, JobListResponse, DataListResponse, HealthCheckResponse, ErrorResponse
)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Request models
class JobCreate(BaseModel):
    name: str
    url: str
    max_pages: int = 10

def analyze_content_with_ai(content: str, title: str) -> dict:
    """Analyze content using Gemini AI"""
    try:
        if not GEMINI_API_KEY:
            return {"summary": "AI analysis not available", "confidence": 0.5}
        
        prompt = f"""
        Analyze this web content and provide:
        1. A brief summary (max 200 characters)
        2. Main topics/categories
        3. Content quality score (0-1)
        4. Key information extracted
        
        Title: {title}
        Content: {content[:1000]}  # Limit content for API
        
        Respond in JSON format with keys: summary, topics, quality_score, key_info
        """
        
        response = model.generate_content(prompt)
        # Parse AI response (simplified)
        return {
            "summary": response.text[:200] if response.text else "No summary available",
            "confidence": 0.8,
            "ai_analysis": response.text
        }
    except Exception as e:
        print(f"AI analysis error: {e}")
        return {"summary": "AI analysis failed", "confidence": 0.3}

def scrape_website(job_id: str, url: str, max_pages: int = 1):
    """Background task to scrape website with database storage"""
    db = next(get_db())
    try:
        # Update job status to running
        job = db.query(ScrapingJobORM).filter(ScrapingJobORM.id == job_id).first()
        if job:
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.utcnow()
            db.commit()
        
        # Use rotating user agents from environment or secure default
        user_agents = os.getenv("SCRAPER_USER_AGENTS", "").split(",") if os.getenv("SCRAPER_USER_AGENTS") else [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        import random
        headers = {
            'User-Agent': random.choice(user_agents).strip()
        }
        
        pages_scraped = 0
        for page in range(min(max_pages, 5)):  # Limit to 5 pages max
            try:
                # Add delay to be respectful
                if page > 0:
                    time.sleep(2)
                
                start_time = time.time()
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                load_time = time.time() - start_time
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text().strip() if title else f"Page {page + 1}"
                
                # Extract content
                paragraphs = soup.find_all('p')
                content_parts = []
                for p in paragraphs[:5]:  # First 5 paragraphs
                    text = p.get_text().strip()
                    if text and len(text) > 20:
                        content_parts.append(text[:300])
                
                content_text = " | ".join(content_parts) if content_parts else "No content extracted"
                
                # AI analysis
                ai_result = analyze_content_with_ai(content_text, title_text)
                
                # Create scraped data record
                scraped_data = ScrapedDataORM(
                    id=str(uuid4()),
                    job_id=job_id,
                    url=url,
                    content={
                        "title": title_text,
                        "text": content_text,
                        "page_number": page + 1
                    },
                    raw_html=str(response.content)[:5000],  # Limit size
                    confidence_score=ai_result.get("confidence", 0.5),
                    ai_processed=True,
                    ai_metadata=ai_result,
                    content_length=len(content_text),
                    load_time=load_time,
                    extracted_at=datetime.utcnow()
                )
                
                db.add(scraped_data)
                pages_scraped += 1
                
            except Exception as e:
                print(f"Error scraping page {page + 1}: {e}")
                continue
        
        # Update job status to completed
        if job:
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()
            job.pages_completed = pages_scraped
            job.total_pages = max_pages
            db.commit()
                
    except Exception as e:
        print(f"Error in scraping job {job_id}: {e}")
        # Update job status to failed
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Web Scraper API",
        description="Simple web scraping API",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/api/v1/health", response_model=HealthCheckResponse)
    async def health_check():
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_connected=True,
            services={
                "api": "healthy",
                "database": "healthy",
                "ai_service": "healthy" if GEMINI_API_KEY else "disabled"
            }
        )
    
    @app.get("/api/v1/scraping/jobs", response_model=JobListResponse)
    async def list_jobs(db: Session = Depends(get_db)):
        jobs = db.query(ScrapingJobORM).order_by(ScrapingJobORM.created_at.desc()).all()
        job_list = []
        for job in jobs:
            job_list.append({
                "id": job.id,
                "name": job.config.get("name", "Unnamed Job"),
                "url": job.url,
                "max_pages": job.config.get("max_pages", 1),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "pages_completed": job.pages_completed,
                "total_pages": job.total_pages,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "priority": job.priority
            })
        return JobListResponse(jobs=job_list, total=len(job_list))
    
    @app.post("/api/v1/scraping/jobs", response_model=JobResponse)
    async def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
        try:
            job_id = str(uuid4())
            
            # Create scraping config with validation
            config = ScrapingConfig(
                name=job_data.name,
                max_pages=job_data.max_pages
            )
            
            new_job = ScrapingJobORM(
                id=job_id,
                url=job_data.url,
                status=JobStatus.PENDING.value,
                config=config.model_dump(),
                created_at=datetime.utcnow(),
                total_pages=job_data.max_pages
            )
            
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            
            job_response = {
                "id": new_job.id,
                "name": job_data.name,
                "url": new_job.url,
                "max_pages": job_data.max_pages,
                "status": new_job.status,
                "created_at": new_job.created_at.isoformat(),
                "total_pages": new_job.total_pages,
                "pages_completed": new_job.pages_completed,
                "config": new_job.config
            }
            
            return JobResponse(
                message="Job created successfully",
                job=job_response
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create job: {str(e)}")
    
    @app.put("/api/v1/scraping/jobs/{job_id}/start")
    async def start_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
        job = db.query(ScrapingJobORM).filter(ScrapingJobORM.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.RUNNING.value:
            max_pages = job.config.get("max_pages", 1)
            background_tasks.add_task(scrape_website, job_id, job.url, max_pages)
            return {"message": f"Job {job_id} started"}
        else:
            return {"message": f"Job {job_id} is already running"}
    
    @app.delete("/api/v1/scraping/jobs/{job_id}")
    async def delete_job(job_id: str, db: Session = Depends(get_db)):
        job = db.query(ScrapingJobORM).filter(ScrapingJobORM.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Delete associated scraped data
        db.query(ScrapedDataORM).filter(ScrapedDataORM.job_id == job_id).delete()
        db.delete(job)
        db.commit()
        return {"message": f"Job {job_id} deleted"}
    
    @app.get("/api/v1/data")
    async def get_scraped_data(db: Session = Depends(get_db)):
        data = db.query(ScrapedDataORM).order_by(ScrapedDataORM.extracted_at.desc()).all()
        data_list = []
        for item in data:
            job = db.query(ScrapingJobORM).filter(ScrapingJobORM.id == item.job_id).first()
            job_name = job.config.get("name", "Unknown") if job else "Unknown"
            
            data_list.append({
                "job_id": item.job_id,
                "job_name": job_name,
                "url": item.url,
                "title": item.content.get("title", "No title"),
                "content": item.content.get("text", "No content")[:200] + "...",
                "scraped_at": item.extracted_at.isoformat(),
                "scraped_date": item.extracted_at.strftime("%Y-%m-%d"),
                "confidence_score": item.confidence_score,
                "ai_processed": item.ai_processed
            })
        return {"data": data_list, "total": len(data_list)}
    
    @app.delete("/api/v1/data")
    async def clear_scraped_data(db: Session = Depends(get_db)):
        db.query(ScrapedDataORM).delete()
        db.commit()
        return {"message": "All scraped data cleared"}
    
    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root():
    return {"message": "Web Scraper API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )