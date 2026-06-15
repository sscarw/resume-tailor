# Resume Tailor

![Python](https://img.shields.io/badge/Python-3.13-blue)
![OpenAI Agents SDK](https://img.shields.io/badge/OpenAI-Agents_SDK-green)
![MCP](https://img.shields.io/badge/MCP-Custom_Server-orange)
![Google Drive](https://img.shields.io/badge/Google_Drive-API-red)
![Pydantic](https://img.shields.io/badge/Pydantic-Structured_Outputs-purple)
![AsyncIO](https://img.shields.io/badge/AsyncIO-Concurrent_Tasks-yellow)

Resume Tailor is an AI-powered resume analysis pipeline built with the OpenAI Agents SDK and a custom MCP server.

The project automatically compares a resume against multiple job descriptions, identifies skill gaps, generates personalized cover letters, and stores results in Google Drive.

---

## What it does

* Analyzes job descriptions stored in Google Drive
* Compares resume content against job requirements
* Generates structured gap analysis reports
* Calculates resume-to-job coverage scores
* Creates personalized cover letters
* Processes multiple job descriptions in batch mode
* Uploads generated reports back to Google Drive

---

## Architecture

The system uses three specialized AI agents and a custom MCP server.

### Agents

#### Job Analyst

* Reads job descriptions from Google Drive
* Extracts structured requirements
* Produces `JobRequirements`

#### Resume Reviewer

* Compares resume content against job requirements
* Identifies matched and missing skills
* Produces `GapAnalysis`

#### Cover Letter Writer

* Generates personalized cover letters
* Uses resume content and gap analysis
* Avoids inventing experience not present in the resume

### MCP Server

Custom Google Drive MCP server providing:

* `list_files_in_folder()`
* `read_drive_file()`
* `upload_file_to_folder()`

### Data Flow

```text
Google Drive
      │
      ▼
+------------------+
|   Job Analyst    |
+------------------+
      │
      ▼
JobRequirements
      │
      ▼
+------------------+
| Resume Reviewer  |
+------------------+
      │
      ▼
 GapAnalysis
      │
      ▼
+------------------+
| Cover Letter AI  |
+------------------+
      │
      ▼
Generated Reports
      │
      ▼
Google Drive
```

---

## Tech Stack

* Python 3.13
* OpenAI Agents SDK
* Model Context Protocol (Custom MCP Server)
* Google Drive API (OAuth 2.0)
* Pydantic
* asyncio

---

## How it works

1. Upload your resume to the `ResumeTailor` folder in Google Drive.
2. Upload job descriptions to the `jobs` folder.
3. Run the pipeline.
4. The system:

   * reads all job descriptions
   * analyzes requirements
   * compares them with the resume
   * generates gap analysis reports
   * generates cover letters
5. Results are uploaded to the `tailored` folder.

---

## Setup

### Install dependencies

```bash
pip install openai-agents
pip install google-api-python-client
pip install google-auth
pip install google-auth-oauthlib
pip install python-dotenv
pip install "mcp[cli]"
```

### Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key
```

### Google Drive Credentials

Place:

```text
credentials.json
```

in the project root directory.

Run the project once and complete OAuth authentication.

A `token.json` file will be created automatically.

### Required Google Drive Structure

```text
ResumeTailor/
│
├── jobs/
│   ├── job_1.txt
│   ├── job_2.txt
│   ├── job_3.txt
│   └── ...
│
├── tailored/
│
└── my_resume.txt
```

### Run

```bash
python pipeline.py
```

---

## Key Features

* Multi-agent architecture
* Custom MCP server integration
* Google Drive automation
* Structured outputs with Pydantic
* Batch processing of job descriptions
* Automatic cover letter generation
* Async task orchestration with asyncio
* Error handling and reporting
* Resume caching (resume is read once and reused across all jobs)

---

## Future Improvements

* ATS score calculation
* Resume rewriting agent
* Retrieval-Augmented Generation (RAG)
* Vector database integration
* LinkedIn profile import
* Support for PDF and DOCX resumes
* Web dashboard for managing applications
* Interview preparation agent
