# Migration Guide: Breaking Changes

## 🔄 Pydantic v2 Migration (v1 → v2)

### Model Configuration Changes
```python
# OLD (Pydantic v1)
class MyModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# NEW (Pydantic v2)
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
```

### Field Validation Changes
```python
# OLD (Pydantic v1)
from pydantic import validator

class MyModel(BaseModel):
    @validator('field_name')
    def validate_field(cls, v):
        return v

# NEW (Pydantic v2)
from pydantic import field_validator

class MyModel(BaseModel):
    @field_validator('field_name')
    @classmethod
    def validate_field(cls, v):
        return v
```

### Model Validation Changes
```python
# OLD (Pydantic v1)
@root_validator
def validate_model(cls, values):
    return values

# NEW (Pydantic v2)
@model_validator(mode='before')  # or mode='after'
@classmethod
def validate_model(cls, values):
    return values
```

## 🗄️ SQLAlchemy 2.0 Migration

### Query Syntax Updates
```python
# OLD (SQLAlchemy 1.4)
users = session.query(User).filter(User.name == 'John').all()

# NEW (SQLAlchemy 2.0)
from sqlalchemy import select
stmt = select(User).where(User.name == 'John')
users = session.execute(stmt).scalars().all()
```

### Session Handling
```python
# OLD
session.add(user)
session.commit()

# NEW (Recommended)
with session.begin():
    session.add(user)
# Auto-commits on exit
```

### Async Support
```python
# NEW Async Pattern
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(session: AsyncSession, user_id: int):
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

## 🚀 FastAPI Updates

### Dependency Injection Improvements
```python
# OLD
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Item).offset(skip).limit(limit).all()

# NEW (More explicit)
@app.get("/items/", response_model=List[ItemResponse])
async def read_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
) -> List[ItemResponse]:
    stmt = select(Item).offset(skip).limit(limit)
    items = db.execute(stmt).scalars().all()
    return items
```

### Response Model Handling
```python
# Enhanced response models
from fastapi import status

@app.post("/items/", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate) -> ItemResponse:
    # Implementation
    pass
```

## 🔧 Code Updates Required

### 1. Update Model Files
```bash
# Check current Pydantic models
grep -r "class Config" src/models/
grep -r "@validator" src/models/
grep -r "@root_validator" src/models/
```

### 2. Update Database Queries
```bash
# Check SQLAlchemy usage
grep -r "session.query" src/
grep -r "\.filter(" src/
```

### 3. Update API Endpoints
```bash
# Check FastAPI patterns
grep -r "@app\." src/api/
grep -r "Depends(" src/api/
```

## 🧪 Testing Migration

### Run Migration Tests
```python
# Create test file: tests/test_migration.py
import pytest
from src.models.pydantic_models import ScrapingJob

def test_pydantic_v2_compatibility():
    """Test Pydantic v2 model creation"""
    job = ScrapingJob(
        url="https://example.com",
        config={"max_pages": 10}
    )
    assert job.url == "https://example.com"
    assert job.config.max_pages == 10

def test_sqlalchemy_v2_queries():
    """Test SQLAlchemy v2 query syntax"""
    from sqlalchemy import select
    from src.models.database_models import ScrapingJobORM
    
    stmt = select(ScrapingJobORM).where(ScrapingJobORM.id == "test")
    assert stmt is not None
```

### Validation Checklist
- [ ] All Pydantic models use v2 syntax
- [ ] All SQLAlchemy queries use v2 syntax  
- [ ] FastAPI endpoints have proper type hints
- [ ] Tests pass with new versions
- [ ] No deprecation warnings in logs

## 🚨 Rollback Plan

If issues occur, you can temporarily pin to older versions:

```toml
# Emergency rollback versions
"pydantic>=2.5.0,<2.6.0",
"sqlalchemy>=2.0.0,<2.0.25",
"fastapi>=0.104.0,<0.109.0",
```

## 📞 Support Resources

- **Pydantic v2 Migration**: https://docs.pydantic.dev/latest/migration/
- **SQLAlchemy 2.0 Migration**: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
- **FastAPI Updates**: https://fastapi.tiangolo.com/release-notes/