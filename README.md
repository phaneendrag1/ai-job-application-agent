# AI Job Application Agent

An AI-powered job application assistant that analyzes resumes against job descriptions and generates tailored resumes and cover letters.

## Features

- Upload PDF or DOCX resumes
- Analyze resume-to-job-description match
- Generate a match score
- Identify matching skills
- Identify skill gaps
- Compare required and candidate experience
- Extract important job keywords
- Generate a tailored resume
- Generate a personalized cover letter
- Download tailored resume as DOCX
- Download cover letter as DOCX

## Tech Stack

- React
- Vite
- Python
- FastAPI
- OpenAI API
- pypdf
- python-docx

## How It Works

1. Upload a resume.
2. Enter a job description.
3. Analyze the job.
4. Review matching skills and skill gaps.
5. Generate a tailored resume.
6. Generate a personalized cover letter.
7. Download the generated documents.

## Architecture

```text
React / Vite
     |
     v
FastAPI Backend
     |
     v
OpenAI API