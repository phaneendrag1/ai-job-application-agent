# 🤖 AI Job Application Agent

An AI-powered job application assistant that analyzes a job posting against a resume, identifies skill gaps, tailors the resume, and generates a personalized cover letter.

## 🚀 Live Demo

https://ai-job-application-agent-swart.vercel.app/

## ✨ Features

- Upload a resume in PDF or DOCX format
- Enter a job posting URL
- Automatically extract public Ashby job postings
- Paste a job description manually
- Analyze resume-to-job alignment
- Generate a match score
- Identify matching skills
- Identify skill gaps
- Compare required and candidate experience
- Extract important job keywords
- Generate a job-targeted resume
- Generate a personalized cover letter
- Download the tailored resume as DOCX
- Download the cover letter as DOCX

## 🏗️ Architecture

```text
User
 │
 ▼
React + Vite Frontend
 │
 │ HTTP requests
 ▼
FastAPI Backend
 │
 ├── Resume Parser
 │      ├── PDF
 │      └── DOCX
 │
 ├── Ashby Job Extraction
 │
 └── OpenAI API
        │
        ├── Job Analysis
        ├── Resume Tailoring
        └── Cover Letter Generation
 │
 ▼
Generated Application
 │
 ├── Tailored Resume
 └── Cover Letter