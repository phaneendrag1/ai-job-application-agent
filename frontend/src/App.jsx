import { useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://ai-job-application-agent-1lqj.onrender.com";

function App() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jobUrl, setJobUrl] = useState("");
  const [jobDescription, setJobDescription] = useState("");

  const [analysis, setAnalysis] = useState(null);
  const [tailoredResume, setTailoredResume] = useState("");
  const [coverLetter, setCoverLetter] = useState("");

  const [loading, setLoading] = useState(false);
  const [tailoring, setTailoring] = useState(false);
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false);

  const [error, setError] = useState("");

  const [resumeDownloading, setResumeDownloading] = useState(false);
  const [coverLetterDownloading, setCoverLetterDownloading] = useState(false);

  const handleResumeChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    const fileName = file.name.toLowerCase();

    const validExtension =
      fileName.endsWith(".pdf") || fileName.endsWith(".docx");

    if (!validExtension && !allowedTypes.includes(file.type)) {
      setError("Please upload a PDF or DOCX resume.");
      return;
    }

    setResumeFile(file);
    setError("");
  };

  const validateInput = () => {
    if (!resumeFile) {
      setError("Please upload your resume first.");
      return false;
    }

    if (!jobDescription.trim()) {
      setError("Please paste the job description.");
      return false;
    }

    return true;
  };

  const handleAnalyze = async () => {
    setError("");
    setAnalysis(null);
    setTailoredResume("");
    setCoverLetter("");

    if (!validateInput()) {
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();

      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      if (jobUrl.trim()) {
        formData.append("job_url", jobUrl.trim());
      }

      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Analysis failed (${response.status})`;

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            message = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors
        }

        throw new Error(message);
      }

      const data = await response.json();

      setAnalysis(data);
    } catch (err) {
      console.error("Analyze error:", err);

      setError(
        err.message ||
          "Failed to connect to the backend. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleTailorResume = async () => {
    setError("");

    if (!resumeFile) {
      setError("Please upload your resume first.");
      return;
    }

    if (!jobDescription.trim()) {
      setError("Please paste the job description first.");
      return;
    }

    setTailoring(true);

    try {
      const formData = new FormData();

      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      const response = await fetch(`${API_URL}/tailor`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Resume tailoring failed (${response.status})`;

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            message = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors
        }

        throw new Error(message);
      }

      const data = await response.json();

      setTailoredResume(
        data.tailored_resume ||
          data.resume ||
          data.content ||
          data.text ||
          ""
      );
    } catch (err) {
      console.error("Tailor error:", err);

      setError(
        err.message ||
          "Failed to tailor the resume. Please try again."
      );
    } finally {
      setTailoring(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    setError("");

    if (!resumeFile) {
      setError("Please upload your resume first.");
      return;
    }

    if (!jobDescription.trim()) {
      setError("Please paste the job description first.");
      return;
    }

    setGeneratingCoverLetter(true);

    try {
      const formData = new FormData();

      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      const response = await fetch(`${API_URL}/cover-letter`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Cover letter generation failed (${response.status})`;

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            message = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors
        }

        throw new Error(message);
      }

      const data = await response.json();

      setCoverLetter(
        data.cover_letter ||
          data.content ||
          data.text ||
          ""
      );
    } catch (err) {
      console.error("Cover letter error:", err);

      setError(
        err.message ||
          "Failed to generate the cover letter. Please try again."
      );
    } finally {
      setGeneratingCoverLetter(false);
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;

    document.body.appendChild(link);
    link.click();
    link.remove();

    window.URL.revokeObjectURL(url);
  };

  const handleDownloadResume = async () => {
    setError("");

    if (!resumeFile) {
      setError("Please upload your resume first.");
      return;
    }

    if (!jobDescription.trim()) {
      setError("Please provide the job description first.");
      return;
    }

    setResumeDownloading(true);

    try {
      const formData = new FormData();

      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      const response = await fetch(`${API_URL}/download-resume`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Resume download failed (${response.status})`;

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            message = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors
        }

        throw new Error(message);
      }

      const blob = await response.blob();

      downloadBlob(blob, "tailored_resume.docx");
    } catch (err) {
      console.error("Resume download error:", err);

      setError(
        err.message ||
          "Failed to download the tailored resume."
      );
    } finally {
      setResumeDownloading(false);
    }
  };

  const handleDownloadCoverLetter = async () => {
    setError("");

    if (!resumeFile) {
      setError("Please upload your resume first.");
      return;
    }

    if (!jobDescription.trim()) {
      setError("Please provide the job description first.");
      return;
    }

    setCoverLetterDownloading(true);

    try {
      const formData = new FormData();

      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      const response = await fetch(
        `${API_URL}/download-cover-letter`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let message = `Cover letter download failed (${response.status})`;

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            message = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors
        }

        throw new Error(message);
      }

      const blob = await response.blob();

      downloadBlob(blob, "cover_letter.docx");
    } catch (err) {
      console.error("Cover letter download error:", err);

      setError(
        err.message ||
          "Failed to download the cover letter."
      );
    } finally {
      setCoverLetterDownloading(false);
    }
  };

  const getValue = (object, keys, fallback = "") => {
    if (!object) {
      return fallback;
    }

    for (const key of keys) {
      if (
        object[key] !== undefined &&
        object[key] !== null
      ) {
        return object[key];
      }
    }

    return fallback;
  };

  const matchingSkills = getValue(
    analysis,
    ["matching_skills", "matchingSkills", "skills"],
    []
  );

  const skillGaps = getValue(
    analysis,
    ["skill_gaps", "skillGaps", "gaps"],
    []
  );

  const keywords = getValue(
    analysis,
    ["keywords", "important_keywords", "importantKeywords"],
    []
  );

  const experienceMatch = getValue(
    analysis,
    ["experience_match", "experienceMatch"],
    null
  );

  const matchScore = getValue(
    analysis,
    ["match_score", "matchScore", "score"],
    null
  );

  const jobTitle = getValue(
    analysis,
    ["job_title", "jobTitle", "title"],
    "Job"
  );

  const assessment = getValue(
    analysis,
    ["assessment", "summary", "analysis"],
    ""
  );

  const renderList = (items) => {
    if (!Array.isArray(items)) {
      return (
        <p className="muted">
          {items || "No information available."}
        </p>
      );
    }

    if (items.length === 0) {
      return (
        <p className="muted">
          No information available.
        </p>
      );
    }

    return (
      <ul className="result-list">
        {items.map((item, index) => (
          <li key={index}>
            {typeof item === "string"
              ? item
              : JSON.stringify(item)}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="badge">
          ✨ AI-powered job applications
        </div>

        <h1>
          Turn a job posting into a{" "}
          <span>stronger application.</span>
        </h1>

        <p>
          Upload your resume, provide a job posting, and
          let the AI analyze the opportunity, identify
          gaps, tailor your resume, and prepare your cover
          letter.
        </p>
      </header>

      {error && (
        <div className="error-box">
          <div className="error-title">
            ⚠️ Something went wrong
          </div>

          <div className="error-message">
            {error}
          </div>
        </div>
      )}

      <main className="main-grid">
        {/* RESUME */}
        <section className="card">
          <div className="card-header">
            <div className="icon blue">↑</div>

            <div>
              <h2>Your Resume</h2>
              <p>PDF or Word document</p>
            </div>
          </div>

          <label className="upload-box">
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleResumeChange}
            />

            <div className="upload-icon">
              ↑
            </div>

            {resumeFile ? (
              <>
                <strong>{resumeFile.name}</strong>

                <span className="success-text">
                  Resume uploaded
                </span>
              </>
            ) : (
              <>
                <strong>
                  Drop your resume here
                </strong>

                <span>
                  or click to upload
                </span>
              </>
            )}
          </label>

          {resumeFile && (
            <div className="ready">
              ✓ Ready for analysis
            </div>
          )}
        </section>

        {/* JOB POSTING */}
        <section className="card">
          <div className="card-header">
            <div className="icon green">💼</div>

            <div>
              <h2>Job Posting</h2>
              <p>URL or job description</p>
            </div>
          </div>

          <div className="input-wrapper">
            <span>🔗</span>

            <input
              type="url"
              placeholder="https://company.com/jobs/..."
              value={jobUrl}
              onChange={(e) =>
                setJobUrl(e.target.value)
              }
            />
          </div>

          <div className="or">
            <span></span>
            OR
            <span></span>
          </div>

          <textarea
            className="job-textarea"
            placeholder="Paste the complete job description here..."
            value={jobDescription}
            onChange={(e) =>
              setJobDescription(e.target.value)
            }
          />
        </section>

        {/* AI AGENT */}
        <section className="card ai-card">
          <div className="card-header">
            <div className="icon purple">✣</div>

            <div>
              <h2>AI Agent</h2>
              <p>Application preparation</p>
            </div>
          </div>

          <div className="agent-actions">
            <div className="agent-item">
              📄 Analyze job requirements
            </div>

            <div className="agent-item">
              💼 Compare your experience
            </div>

            <div className="agent-item">
              🎯 Identify skill gaps
            </div>

            <div className="agent-item">
              ✨ Prepare application
            </div>
          </div>

          <button
            className="primary-button"
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading
              ? "Analyzing..."
              : "Analyze Job →"}
          </button>
        </section>
      </main>

      {/* ANALYSIS */}
      {analysis && (
        <section className="results-section">
          <div className="section-heading">
            <div>
              <span className="small-label">
                AI ANALYSIS COMPLETE
              </span>

              <h2>Application Analysis</h2>

              <p>
                Here's how your profile compares with this
                role.
              </p>
            </div>
          </div>

          <div className="analysis-grid">
            <div className="score-card">
              <span>Match Score</span>

              <strong>
                {matchScore !== null
                  ? matchScore
                  : "—"}
              </strong>

              <small>/100</small>
            </div>

            <div className="info-card">
              <span>Job Title</span>

              <h3>{jobTitle}</h3>
            </div>

            <div className="info-card">
              <span>Assessment</span>

              <p>
                {assessment ||
                  "Analysis completed successfully."}
              </p>
            </div>
          </div>

          <div className="results-grid">
            <div className="result-card">
              <h3>✓ Matching Skills</h3>

              <p className="result-description">
                Skills supported by your resume
              </p>

              {renderList(matchingSkills)}
            </div>

            <div className="result-card">
              <h3>◎ Skill Gaps</h3>

              <p className="result-description">
                Requirements needing attention
              </p>

              {renderList(skillGaps)}
            </div>
          </div>

          {experienceMatch && (
            <div className="result-card full-width">
              <h3>💼 Experience Match</h3>

              <p className="result-description">
                Comparison between the role and your
                background
              </p>

              {typeof experienceMatch === "string" ? (
                <p>{experienceMatch}</p>
              ) : (
                <div className="experience-grid">
                  {experienceMatch.required && (
                    <div>
                      <strong>Required</strong>
                      <p>
                        {experienceMatch.required}
                      </p>
                    </div>
                  )}

                  {experienceMatch.candidate && (
                    <div>
                      <strong>Candidate</strong>
                      <p>
                        {experienceMatch.candidate}
                      </p>
                    </div>
                  )}

                  {experienceMatch.assessment && (
                    <div>
                      <strong>Assessment</strong>
                      <p>
                        {experienceMatch.assessment}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="result-card full-width">
            <h3>🔑 Important Keywords</h3>

            <div className="keyword-container">
              {Array.isArray(keywords) ? (
                keywords.map((keyword, index) => (
                  <span
                    className="keyword"
                    key={index}
                  >
                    {typeof keyword === "string"
                      ? keyword
                      : JSON.stringify(keyword)}
                  </span>
                ))
              ) : (
                <p>{keywords || "No keywords found."}</p>
              )}
            </div>
          </div>

          {/* APPLICATION ACTIONS */}
          <div className="prepare-card">
            <div>
              <span className="small-label">
                PREPARE YOUR APPLICATION
              </span>

              <h2>
                Tailor your resume and generate a
                personalized cover letter.
              </h2>
            </div>

            <div className="prepare-buttons">
              <button
                className="secondary-button"
                onClick={handleTailorResume}
                disabled={tailoring}
              >
                {tailoring
                  ? "Tailoring Resume..."
                  : "Tailor My Resume"}
              </button>

              <button
                className="primary-button"
                onClick={handleGenerateCoverLetter}
                disabled={generatingCoverLetter}
              >
                {generatingCoverLetter
                  ? "Generating..."
                  : "Generate Cover Letter"}
              </button>
            </div>
          </div>
        </section>
      )}

      {/* TAILORED RESUME */}
      {tailoredResume && (
        <section className="document-section">
          <div className="document-header">
            <div>
              <span className="small-label">
                TAILORED RESUME
              </span>

              <h2>
                Tailored for this specific job
              </h2>
            </div>

            <button
              className="download-button"
              onClick={handleDownloadResume}
              disabled={resumeDownloading}
            >
              {resumeDownloading
                ? "Preparing..."
                : "↓ Download Resume"}
            </button>
          </div>

          <div className="document-content">
            <pre>{tailoredResume}</pre>
          </div>
        </section>
      )}

      {/* COVER LETTER */}
      {coverLetter && (
        <section className="document-section">
          <div className="document-header">
            <div>
              <span className="small-label">
                COVER LETTER
              </span>

              <h2>
                Personalized for this job
              </h2>
            </div>

            <button
              className="download-button"
              onClick={handleDownloadCoverLetter}
              disabled={coverLetterDownloading}
            >
              {coverLetterDownloading
                ? "Preparing..."
                : "↓ Download Cover Letter"}
            </button>
          </div>

          <div className="cover-letter-content">
            {coverLetter}
          </div>
        </section>
      )}

      <footer>
        <p>
          AI Job Application Agent · Built with React,
          FastAPI & OpenAI
        </p>

        <p className="api-status">
          Backend: {API_URL}
        </p>
      </footer>
    </div>
  );
}

export default App;