# Health AI Agent

A containerized FastAPI application for analyzing medical discharge summaries using the Med42 language model. This system provides AI-powered summarization and analytics for MIMIC-III hospital discharge data.

## Features

- **AI-Powered Summarization**: Generate concise summaries using Med42-8B model via HuggingFace API
- **Patient Management**: Complete CRUD operations for hospital admissions
- **Advanced Search**: Filter patients by diagnosis, admission type, demographics
- **Containerized Deployment**: Full Docker setup with PostgreSQL database
- **RESTful API**: OpenAPI documentation with interactive testing

## Quick Start

### Prerequisites
- Docker and Docker Compose
- HuggingFace API token (Read token) ([get one here](https://huggingface.co/settings/tokens))


### Environment Configuration
In the .env file, fill the <b>HF_TOKEN=[YOUR TOKEN]</b> with your actual HF (with Read permission) token. 

<b> [NOTE]: </b> Check the ports for the Database (POSTGRES_PORT=5432) and for the API (API_PORT=8000).
Make sure you are not using the same ports for other aplications!

```bash
# AI Configuration
HF_TOKEN=your_huggingface_token_here
```

### Deploy with Docker
```bash
# Start all services
docker-compose up --build -d

# Create database tables
docker-compose exec health-ai-api python health_ai_agent/scripts/create_tables.py

# Load MIMIC data
docker-compose exec health-ai-api python health_ai_agent/scripts/load_data.py /path/to/mimic_data.parquet

# Check status
docker-compose ps

# To properly restart the container
docker-compose down --volumes && docker-compose up --build -d
```

### 4. Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Database Admin**: http://localhost:8080
- **Health Check**: http://localhost:8000/health/

## API Endpoints

### Health Monitoring
```bash
GET /health/                    # Basic health check
GET /health/database           # Database connectivity
GET /health/ai                 # AI model status
```

### Patient Management
```bash
GET /patients/list             # List patients with search/filtering
GET /patients/{hadm_id}        # Get specific patient details
POST /patients/               # Create new patient record
DELETE /patients/{hadm_id}     # Delete patient and summaries
```

### AI Operations
```bash
POST /ai/summarize            # Generate discharge summary
GET /ai/summaries             # List recent summaries
GET /ai/summaries/{id}        # Get specific summary
GET /ai/summaries/patient/{hadm_id}  # Get patient's summaries
DELETE /ai/summaries/{id}     # Delete specific summary
DELETE /ai/summaries/patient/{hadm_id}  # Delete patient's summaries
```

#### <i> <b> [NOTE] :Use the API documentation to interact with the endpoints! </b> </i>
### Get Analytics
```bash
# AI usage statistics
curl "http://localhost:8000/ai/stats"

# Patient demographics
curl "http://localhost:8000/patients/stats"
```

## Development Setup

### Local Installation
```bash
# Install dependencies with uv
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your database credentials and HF_TOKEN

# Start local database (if not using Docker)
# Update POSTGRES_HOST=localhost in .env

# Run database setup
uv run python health_ai_agent/scripts/create_tables.py

# Load sample data
uv run python health_ai_agent/scripts/load_data.py path/to/data.parquet

# Start development server
uv run uvicorn health_ai_agent.main:app --reload
```

### Project Structure
```
health-ai-agent/
├── README.md                    # This file
├── docker-compose.yml           # Production deployment
├── Dockerfile                   # Container definition
├── pyproject.toml              # Python dependencies
├── .env                        # Environment configuration
├── health_ai_agent/            # Main application package
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration management
│   ├── api/                    # API route handlers
│   │   ├── health.py           # Health check endpoints
│   │   ├── patients.py         # Patient CRUD operations
│   │   └── ai.py               # AI summarization endpoints
│   ├── schemas/                # Pydantic request/response models
│   │   ├── patient.py          # Patient data schemas
│   │   └── ai.py               # AI operation schemas
│   ├── services/               # Business logic layer
│   │   ├── database.py         # Database models and connection
│   │   └── ai_services.py      # AI service integration
│   └── scripts/                # Utility scripts
│       ├── create_tables.py    # Database initialization
│       └── load_data.py        # MIMIC data loading
```

## Data Format

The application expects MIMIC-III discharge summary data with these fields:
- `HADM_ID`: Hospital admission ID (primary key)
- `SUBJECT_ID`: Patient subject ID
- `GENDER`: Patient gender (M/F)
- `AGE_CORRECTED`: Patient age
- `ADMISSION_TYPE`: Type of admission (EMERGENCY, ELECTIVE, etc.)
- `DIAGNOSIS`: Primary diagnosis
- `TEXT`: Full discharge summary text
- `HOSPITAL_EXPIRE_FLAG`: Boolean indicating in-hospital mortality

## Architecture

### Components
- **FastAPI Application**: REST API with automatic OpenAPI documentation
- **PostgreSQL Database**: Persistent storage for patient data and AI summaries
- **Med42-8B Model**: Medical language model via HuggingFace Inference API
- **Docker Containers**: Isolated, reproducible deployment environment

### Data Flow
1. Patient data stored in `mimic_discharge_summaries` table
2. AI summaries generated on-demand and cached in `ai_summaries` table
3. RESTful API provides access to both original data and AI insights



### Environment Variables
All configuration through environment variables for container compatibility:

```bash
# Database Configuration
POSTGRES_DB=health_ai_db
POSTGRES_USER=health_ai
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=postgres 
POSTGRES_PORT=5432

# AI Model Configuration
MODEL_NAME=m42-health/Llama3-Med42-8B
HF_TOKEN=hf_your_token_here
USE_API=true

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### Docker Compose Services
- `postgres`: PostgreSQL 15 database with health checks
- `health-ai-api`: Main application container
- `adminer`: Web-based database administration (optional)

## Troubleshooting (can also be done interactively through the FastAPI docs)

### Common Issues

1. **AI Service Unavailable**
   ```bash
   # Check HF_TOKEN is set correctly
   curl http://localhost:8000/health/ai
   ```

2. **Database Connection Failed**
   ```bash
   # Verify database is running
   docker-compose logs postgres
   curl http://localhost:8000/health/database
   ```

3. **Module Import Errors**
   ```bash
   # Use uv run for script execution
   docker-compose exec health-ai-api uv run python health_ai_agent/scripts/create_tables.py
   ```

### Debugging
```bash
# View application logs
docker-compose logs health-ai-api

# Check all services status
docker-compose ps

# Access container shell
docker-compose exec health-ai-api bash

# Test database connection
docker-compose exec postgres pg_isready -U health_ai
```

### Future Work

```bash
-> Implement persistent conversations between the user and the AI based on each patient

-> Implement a React based UI
```

