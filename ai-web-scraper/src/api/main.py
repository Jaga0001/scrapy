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
    """Analyze content using Gemini AI with standardized response format"""
    try:
        if not GEMINI_API_KEY:
            return {
                "summary": "AI analysis not available - API key not configured",
                "confidence": 0.0,
                "topics": [],
                "quality_score": 0.5,
                "key_info": [],
                "ai_model": "gemini-2.0-flash-exp",
                "processing_status": "disabled"
            }
        
        prompt = f"""
        Analyze this web content and provide a JSON response with the following structure:
        {{
            "summary": "Brief summary (max 200 characters)",
            "topics": ["topic1", "topic2", "topic3"],
            "quality_score": 0.8,
            "key_info": ["key point 1", "key point 2"],
            "content_category": "news|blog|product|documentation|other",
            "language": "detected language code",
            "readability_score": 0.7
        }}
        
        Title: {title}
        Content: {content[:2000]}
        
        Respond only with valid JSON.
        """
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            try:
                # Try to parse as JSON first
                import json
                ai_result = json.loads(response.text.strip())
                
                # Validate and standardize the response
                standardized_result = {
                    "summary": str(ai_result.get("summary", ""))[:200],
                    "confidence": min(max(float(ai_result.get("quality_score", 0.5)), 0.0), 1.0),
                    "topics": ai_result.get("topics", [])[:5],  # Limit to 5 topics
                    "quality_score": min(max(float(ai_result.get("quality_score", 0.5)), 0.0), 1.0),
                    "key_info": ai_result.get("key_info", [])[:10],  # Limit to 10 key points
                    "content_category": ai_result.get("content_category", "other"),
                    "language": ai_result.get("language", "unknown"),
                    "readability_score": min(max(float(ai_result.get("readability_score", 0.5)), 0.0), 1.0),
                    "ai_model": "gemini-2.0-flash-exp",
                    "processing_status": "success",
                    "raw_response": response.text[:500]  # Keep first 500 chars of raw response
                }
                
                return standardized_result
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # Fallback to text parsing if JSON parsing fails
                return {
                    "summary": response.text[:200] if response.text else "No summary available",
                    "confidence": 0.6,
                    "topics": [],
                    "quality_score": 0.6,
                    "key_info": [],
                    "content_category": "other",
                    "language": "unknown",
                    "readability_score": 0.5,
                    "ai_model": "gemini-2.0-flash-exp",
                    "processing_status": "partial_success",
                    "raw_response": response.text[:500],
                    "parsing_error": str(e)
                }
        else:
            return {
                "summary": "AI analysis returned empty response",
                "confidence": 0.3,
                "topics": [],
                "quality_score": 0.3,
                "key_info": [],
                "content_category": "other",
                "language": "unknown",
                "readability_score": 0.5,
                "ai_model": "gemini-2.0-flash-exp",
                "processing_status": "empty_response"
            }
            
    except Exception as e:
        print(f"AI analysis error: {e}")
        return {
            "summary": "AI analysis failed due to error",
            "confidence": 0.2,
            "topics": [],
            "quality_score": 0.2,
            "key_info": [],
            "content_category": "other",
            "language": "unknown",
            "readability_score": 0.5,
            "ai_model": "gemini-2.0-flash-exp",
            "processing_status": "error",
            "error_message": str(e)
        }

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
    
    # Secure CORS configuration
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
    cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,  # Disabled for security unless specifically needed
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
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
            # Ensure consistent field mapping
            job_dict = {
                "id": job.id,
                "name": job.config.get("name", "Unnamed Job"),
                "url": job.url,
                "max_pages": job.config.get("max_pages", job.total_pages or 1),
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "pages_completed": job.pages_completed or 0,
                "total_pages": job.total_pages or 0,
                "error_message": job.error_message,
                "retry_count": job.retry_count or 0,
                "priority": job.priority or 5,
                "user_id": job.user_id,
                "tags": job.tags or [],
                "config": job.config or {}
            }
            job_list.append(job_dict)
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
    
    @app.get("/api/v1/data", response_model=DataListResponse)
    async def get_scraped_data(db: Session = Depends(get_db)):
        data = db.query(ScrapedDataORM).order_by(ScrapedDataORM.extracted_at.desc()).all()
        data_list = []
        for item in data:
            job = db.query(ScrapingJobORM).filter(ScrapingJobORM.id == item.job_id).first()
            job_name = job.config.get("name", "Unknown") if job else "Unknown"
            
            # Ensure consistent data structure for export compatibility
            content_text = ""
            if item.content and isinstance(item.content, dict):
                content_text = item.content.get("text", "")
                if isinstance(content_text, str) and len(content_text) > 200:
                    content_text = content_text[:200] + "..."
            
            data_dict = {
                "id": item.id,
                "job_id": item.job_id,
                "job_name": job_name,
                "url": item.url,
                "title": item.content.get("title", "No title") if item.content else "No title",
                "content": content_text,
                "scraped_at": item.extracted_at.isoformat() if item.extracted_at else None,
                "scraped_date": item.extracted_at.strftime("%Y-%m-%d") if item.extracted_at else None,
                "confidence_score": float(item.confidence_score) if item.confidence_score else 0.0,
                "ai_processed": bool(item.ai_processed),
                "data_quality_score": float(item.data_quality_score) if item.data_quality_score else 0.0,
                "content_length": int(item.content_length) if item.content_length else 0,
                "load_time": float(item.load_time) if item.load_time else 0.0,
                "content_type": item.content_type or "html",
                "validation_errors": item.validation_errors or []
            }
            data_list.append(data_dict)
        return DataListResponse(data=data_list, total=len(data_list))
    
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
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )