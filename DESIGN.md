# Design Document: LLM Quiz Solver

## Architecture Overview

The LLM Quiz Solver is a production-ready FastAPI application that automates quiz solving by combining web scraping, file processing, LLM analysis, and data visualization.

## System Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (main.py)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐  ┌─▼──────────┐
│Quiz   │  │LLM Prompt  │
│Solver │  │Challenge   │
└───┬───┘  └────────────┘
    │
    ├─── QuizScraper (Playwright)
    ├─── FileProcessor (PDF, CSV, Excel)
    ├─── LLMAnalyzer (AIPIPE/OpenRouter)
    ├─── QuizVisualizer (Matplotlib)
    └─── QuizDatabase (SQLite/Bolt-like)
```

## Component Design

### 1. FastAPI Application (`main.py`)

**Purpose**: Main API server with endpoints for quiz solving and prompt testing.

**Key Features**:
- Secret validation (403 on invalid secret)
- Async request handling
- 3-minute execution timeout
- Attempt tracking in database
- Chained quiz support

**Endpoints**:
- `POST /solve-quiz`: Main quiz solving endpoint
- `POST /test-prompt`: LLM prompt challenge testing
- `GET /attempt/{id}`: Retrieve quiz attempt
- `GET /health`: Health check

### 2. Quiz Solver (`quiz_solver.py`)

**Purpose**: Orchestrates the entire quiz solving workflow.

**Workflow**:
1. Scrape quiz page (Playwright)
2. Process downloadable files (PDFs, CSVs, etc.)
3. Extract tables from HTML
4. Analyze questions using LLM
5. Generate visualizations if needed
6. Prepare submission data
7. Submit answers and handle chained quizzes

**Design Choices**:
- Async/await for concurrent operations
- Timeout checking at each step
- Error collection and reporting
- Step-by-step progress tracking

### 3. Quiz Scraper (`quiz_scraper.py`)

**Purpose**: Scrape JavaScript-rendered quiz pages.

**Why Playwright?**
- Reliable JavaScript rendering
- Better than Selenium for modern SPAs
- Built-in waiting mechanisms
- Headless browser support

**Features**:
- Full page screenshot (base64)
- Script extraction
- Base64 encoded content extraction
- File link discovery
- Quiz structure extraction

### 4. File Processor (`file_processor.py`)

**Purpose**: Process various file types used in quizzes.

**Supported Formats**:
- PDF: Text, tables, metadata extraction
- CSV: DataFrame conversion, statistics
- Excel: Multi-sheet support
- JSON: Direct parsing
- TXT: Text extraction

**Design Choices**:
- Multiple encoding fallbacks for text files
- pandas for structured data
- pdfplumber for better table extraction than PyPDF2 alone

### 5. LLM Analyzer (`llm_analyzer.py`)

**Purpose**: Interface with AIPIPE/OpenRouter API for LLM analysis.

**Why AIPIPE/OpenRouter?**
- Unified API for multiple LLM providers
- Cost-effective routing
- Easy model switching
- Simple authentication

**Capabilities**:
- Question analysis and answering
- Data extraction from content
- Calculation assistance
- Visualization recommendations

**Design Choices**:
- Temperature set to 0.3 for more consistent results
- JSON parsing for structured responses
- Context truncation to stay within token limits
- Error handling for API failures

### 6. Visualization (`visualization.py`)

**Purpose**: Generate charts as base64-encoded images.

**Supported Chart Types**:
- Bar charts
- Line charts
- Pie charts
- Scatter plots
- Histograms
- Data tables

**Design Choices**:
- Non-interactive backend (Agg) for server environments
- Base64 encoding for easy API response inclusion
- High DPI (150) for clarity
- Automatic figure cleanup to prevent memory leaks

### 7. Database (`database.py`)

**Purpose**: Persist quiz attempts and results.

**Why SQLite (Bolt-like)?**
- Embedded, no external dependencies
- Fast key-value-like operations
- Perfect for quiz result caching
- Simple deployment (single file)

**Schema**:
- `quiz_attempts`: Main attempt records
- `quiz_results`: Individual question results

**Design Choices**:
- JSON serialization for complex data
- Timestamp tracking for analytics
- Status field for state management

### 8. LLM Prompt Challenge (`llm_prompt_challenge.py`)

**Purpose**: Test system prompt protection against code word extraction.

**Features**:
- Random code word generation
- System prompt creation with protection rules
- User prompt for extraction attempts
- Detection of code word leakage

## Security Considerations

1. **Secret Validation**: All quiz solving requires valid secret key
2. **Input Sanitization**: URLs and inputs are validated
3. **Timeout Protection**: 3-minute limit prevents resource exhaustion
4. **Error Handling**: Graceful degradation without exposing internals

## Performance Optimizations

1. **Async Operations**: Concurrent file downloads and API calls
2. **Content Limits**: Truncation of large HTML/text for LLM processing
3. **File Limits**: Max 5 files, 20 questions per quiz
4. **Caching**: Database storage for repeated quiz attempts

## Error Handling Strategy

- **Validation Errors**: Return 400 with clear messages
- **Authentication Errors**: Return 403 for invalid secrets
- **Timeout Errors**: Return 408 and save partial progress
- **Processing Errors**: Collect in errors array, continue processing
- **LLM Errors**: Fallback to alternative strategies or skip

## Testing Strategy

### Unit Tests (Recommended)
- File processor for each file type
- LLM analyzer mock responses
- Visualization generation
- Database operations

### Integration Tests (Recommended)
- End-to-end quiz solving
- Chained quiz flows
- Error scenarios
- Timeout handling

## Deployment Considerations

1. **Environment Variables**: Use `.env` for configuration
2. **Playwright Installation**: Requires `playwright install chromium`
3. **Database Path**: Configurable for different environments
4. **API Keys**: Secure storage via environment variables
5. **Resource Limits**: Consider memory limits for large quizzes

## Future Enhancements

1. **Caching**: Redis for frequently accessed quizzes
2. **Queue System**: Celery for long-running quiz solves
3. **Monitoring**: Prometheus metrics integration
4. **Logging**: Structured logging with correlation IDs
5. **Rate Limiting**: Prevent abuse of API endpoints

## License

MIT License - see LICENSE file


