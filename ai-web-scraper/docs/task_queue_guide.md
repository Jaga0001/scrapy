# Task Queue System Guide

This guide explains how to use the Celery-based task queue system for asynchronous web scraping operations.

## Overview

The task queue system provides:

- **Asynchronous job processing** using Celery with Redis backend
- **Job monitoring and progress tracking** with real-time updates
- **Error handling and retry mechanisms** with circuit breaker patterns
- **Performance metrics and health monitoring** for system optimization
- **Scalable worker architecture** for handling concurrent operations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Job Queue     │    │     Worker      │    │    Monitor      │
│                 │    │                 │    │                 │
│ - Submit jobs   │    │ - Process tasks │    │ - Track progress│
│ - Track status  │    │ - Handle errors │    │ - Collect metrics│
│ - Manage queue  │    │ - Retry logic   │    │ - Health checks │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │      Redis      │
                    │                 │
                    │ - Message broker│
                    │ - Result backend│
                    │ - Job storage   │
                    └─────────────────┘
```

## Components

### 1. JobQueue (`src/pipeline/job_queue.py`)

Manages job submission, status tracking, and queue operations.

**Key Features:**
- Submit scraping jobs with custom configurations
- Track job status and progress
- Cancel running jobs
- Batch job operations
- Queue statistics and cleanup

**Example Usage:**
```python
from src.pipeline.job_queue import get_job_queue
from src.models.pydantic_models import ScrapingConfig

# Get job queue instance
job_queue = get_job_queue()

# Create configuration
config = ScrapingConfig(
    wait_time=5,
    max_retries=3,
    use_stealth=True,
    extract_links=True
)

# Submit job
job = job_queue.submit_scraping_job(
    url="https://example.com",
    config=config,
    priority=3
)

# Check status
status = job_queue.get_job_status(job.id)
print(f"Job status: {status.status}")
```

### 2. Worker (`src/pipeline/worker.py`)

Background workers that process scraping tasks.

**Key Features:**
- Asynchronous task processing
- Circuit breaker protection
- Automatic retry with exponential backoff
- Error handling and logging
- AI content processing integration

**Task Types:**
- `scrape_url_task`: Single URL scraping
- `process_content_task`: AI content processing
- `clean_data_task`: Data cleaning and validation
- `batch_scrape_task`: Multiple URL processing

**Example Worker Startup:**
```bash
# Start Celery worker
celery -A src.pipeline.worker worker --loglevel=info

# Start with specific queues
celery -A src.pipeline.worker worker --queues=scraping,processing --loglevel=info

# Start multiple workers
celery -A src.pipeline.worker worker --concurrency=4 --loglevel=info
```

### 3. JobMonitor (`src/pipeline/monitor.py`)

Real-time monitoring and performance tracking.

**Key Features:**
- Job progress tracking with ETA calculation
- System performance metrics
- Error rate monitoring
- Health status checks
- Historical data analysis

**Example Usage:**
```python
from src.pipeline.monitor import get_job_monitor

# Get monitor instance
monitor = get_job_monitor()

# Get job progress
progress = monitor.get_job_progress(job_id)
print(f"Progress: {progress['progress_percentage']}%")

# Get system metrics
metrics = monitor.get_system_metrics()
print(f"Health: {metrics['health_status']}")
print(f"Active workers: {metrics['worker_stats']['active_workers']}")

# Record job completion
monitor.record_job_completion(job_id, success=True, processing_time=45.5)
```

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Celery Configuration
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=["json"]
CELERY_TIMEZONE=UTC
CELERY_ENABLE_UTC=True
```

### Celery Settings

The system uses the following Celery configuration:

```python
celery_app.conf.update(
    # Task routing
    task_routes={
        "src.pipeline.worker.scrape_url_task": {"queue": "scraping"},
        "src.pipeline.worker.process_content_task": {"queue": "processing"},
        "src.pipeline.worker.clean_data_task": {"queue": "cleaning"},
    },
    
    # Performance settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_events=True,
)
```

## Usage Examples

### Basic Job Submission

```python
from src.pipeline.job_queue import get_job_queue
from src.models.pydantic_models import ScrapingConfig

job_queue = get_job_queue()

# Simple job
job = job_queue.submit_scraping_job("https://example.com")

# Job with custom config
config = ScrapingConfig(
    wait_time=10,
    max_retries=2,
    use_stealth=True,
    extract_images=True,
    custom_selectors={"title": "h1", "content": ".main-content"}
)

job = job_queue.submit_scraping_job(
    url="https://example.com",
    config=config,
    priority=1  # High priority
)
```

### Batch Processing

```python
urls = [
    "https://example1.com",
    "https://example2.com", 
    "https://example3.com"
]

job_ids = []
for url in urls:
    job = job_queue.submit_scraping_job(url, priority=5)
    job_ids.append(job.id)

# Monitor batch progress
active_jobs = job_queue.get_active_jobs()
print(f"Active jobs: {len(active_jobs)}")
```

### Job Monitoring

```python
from src.pipeline.monitor import get_job_monitor

monitor = get_job_monitor()

# Monitor specific job
progress = monitor.get_job_progress(job_id)
if progress.get("status") == "running":
    print(f"Progress: {progress['progress_percentage']}%")
    print(f"ETA: {progress['estimated_completion']}")

# Monitor system health
metrics = monitor.get_system_metrics()
if metrics["health_status"] == "HEALTHY":
    print("System is running normally")
else:
    print(f"System status: {metrics['health_status']}")
```

### Error Handling

```python
# Submit job with error handling
try:
    job = job_queue.submit_scraping_job("https://invalid-url.com")
    
    # Monitor for completion or failure
    while True:
        status = job_queue.get_job_status(job.id)
        if status.status == JobStatus.FAILED:
            print(f"Job failed: {status.error_message}")
            break
        elif status.status == JobStatus.COMPLETED:
            print("Job completed successfully")
            break
        
        time.sleep(1)
        
except Exception as e:
    print(f"Failed to submit job: {e}")
```

## Monitoring and Debugging

### Queue Statistics

```python
# Get queue statistics
stats = job_queue.get_queue_stats()
print(f"Total jobs: {stats['total_jobs']}")
print(f"Status breakdown: {stats['status_counts']}")
print(f"Active tasks: {stats['active_tasks']}")
```

### Performance Metrics

```python
# Get performance history
history = monitor.get_performance_history(hours=24)
for hour_data in history['history']:
    print(f"Hour: {hour_data['timestamp']}")
    print(f"Jobs processed: {hour_data['jobs_processed']}")
    print(f"Success rate: {hour_data['success_rate']}%")
```

### Health Monitoring

```python
# Check system health
metrics = monitor.get_system_metrics()
health = metrics['health_status']

if health == "HEALTHY":
    print("✓ System is healthy")
elif health == "DEGRADED":
    print("⚠ System performance is degraded")
elif health == "UNHEALTHY":
    print("✗ System is unhealthy")
```

## Best Practices

### 1. Job Configuration

- Use appropriate `wait_time` based on target website
- Set reasonable `max_retries` to avoid infinite loops
- Enable `use_stealth` for bot-detection prone sites
- Configure `delay_between_requests` to be respectful

### 2. Error Handling

- Monitor job status regularly
- Implement proper retry logic
- Log errors for debugging
- Use circuit breakers for external services

### 3. Performance Optimization

- Use appropriate worker concurrency
- Monitor queue length and processing times
- Clean up old job records regularly
- Scale workers based on load

### 4. Resource Management

- Monitor Redis memory usage
- Set appropriate task timeouts
- Limit concurrent jobs per worker
- Use job priorities effectively

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   Error: ConnectionError: Error connecting to Redis
   ```
   - Ensure Redis server is running
   - Check Redis URL configuration
   - Verify network connectivity

2. **No Workers Available**
   ```
   Warning: No workers available for task processing
   ```
   - Start Celery workers: `celery -A src.pipeline.worker worker`
   - Check worker logs for errors
   - Verify worker registration

3. **Tasks Stuck in Pending**
   ```
   Jobs remain in PENDING status
   ```
   - Check worker connectivity to Redis
   - Verify task routing configuration
   - Restart workers if necessary

4. **High Memory Usage**
   ```
   Workers consuming excessive memory
   ```
   - Reduce `worker_max_tasks_per_child`
   - Monitor for memory leaks
   - Restart workers periodically

### Debugging Commands

```bash
# Check Celery status
celery -A src.pipeline.worker status

# Monitor tasks in real-time
celery -A src.pipeline.worker events

# Inspect active tasks
celery -A src.pipeline.worker inspect active

# Check worker statistics
celery -A src.pipeline.worker inspect stats
```

## API Reference

### JobQueue Methods

- `submit_scraping_job(url, config, priority)` - Submit new job
- `get_job_status(job_id)` - Get job status
- `update_job_status(job_id, status, **kwargs)` - Update job
- `cancel_job(job_id)` - Cancel job
- `get_active_jobs(limit)` - Get active jobs
- `get_job_history(limit, status_filter)` - Get job history
- `cleanup_old_jobs(max_age_days)` - Clean old jobs
- `get_queue_stats()` - Get queue statistics

### JobMonitor Methods

- `get_job_progress(job_id)` - Get job progress
- `get_system_metrics()` - Get system metrics
- `get_active_jobs_summary()` - Get active jobs summary
- `record_job_completion(job_id, success, time)` - Record completion
- `record_error(job_id, error_type, message)` - Record error
- `get_performance_history(hours)` - Get performance history

### Worker Tasks

- `scrape_url_task(job_id, url, config)` - Scrape single URL
- `process_content_task(content, url, type)` - Process content
- `clean_data_task(data)` - Clean scraped data
- `batch_scrape_task(job_id, urls, config)` - Batch scraping

## Integration

The task queue system integrates with other components:

- **Web Scraper**: Executes scraping operations
- **AI Processor**: Processes scraped content
- **Data Cleaner**: Validates and cleans data
- **Database**: Stores results and metadata
- **API**: Provides REST endpoints for job management
- **Dashboard**: Real-time monitoring interface

For more information, see the individual component documentation.