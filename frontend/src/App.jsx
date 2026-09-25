import React, { useMemo, useState } from "react";
import "./App.css";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function scoreClass(score) {
  if (score >= 80) return "score-good";
  if (score >= 60) return "score-mid";
  return "score-low";
}

function formatError(payload) {
  if (!payload) return "Something went wrong.";
  if (typeof payload === "string") return payload;
  if (payload.detail) return payload.detail;
  return "Something went wrong while building your application.";
}

function App() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  const ats = result?.application?.ats;
  const resume = result?.application?.resume;
  const job = result?.application?.job;
  const coverLetter = result?.application?.cover_letter || "";

  const canBuild = Boolean(resumeFile && jobDescription.trim() && !loading);

  const progress = useMemo(() => {
    if (!loading) return [];
    return [
      "Reading your resume",
      "Understanding the job",
      "Matching your experience",
      "Building your tailored resume",
      "Preparing your cover letter",
    ];
  }, [loading]);

  async function buildApplication() {
    if (!resumeFile || !jobDescription.trim()) {
      setError("Upload your resume and paste the job description first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setActiveTab("overview");

    try {
      const formData = new FormData();
      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription.trim());

      const response = await fetch(`${API_URL}/build-application`, {
        method: "POST",
        body: formData,
      });

      const raw = await response.text();
      let payload = {};
      try {
        payload = raw ? JSON.parse(raw) : {};
      } catch {
        payload = { detail: raw };
      }

      if (!response.ok) {
        throw new Error(formatError(payload));
      }

      setResult(payload);
    } catch (err) {
      setError(err.message || "Unable to build your application.");
    } finally {
      setLoading(false);
    }
  }

  async function downloadResume() {
    if (!resume) return;

    try {
      const response = await fetch(`${API_URL}/download-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resume),
      });

      if (!response.ok) throw new Error("Resume download failed.");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "JobPilot_Tailored_Resume.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function downloadCoverLetter() {
    if (!resume || !job) return;

    try {
      const response = await fetch(`${API_URL}/download-cover-letter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume,
          job,
          cover_letter: coverLetter,
        }),
      });

      if (!response.ok) throw new Error("Cover letter download failed.");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "JobPilot_Cover_Letter.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">J</div>
          <div>
            <strong>JobPilot</strong>
            <span>AI</span>
          </div>
        </div>
        <div className="topbar-note">Resume tailoring, ATS compatibility & cover letter</div>
      </header>

      <main>
        <section className="hero">
          <div className="eyebrow">YOUR JOB APPLICATION COPILOT</div>
          <h1>Turn one resume into a <em>job-ready application.</em></h1>
          <p>
            Upload your resume, paste the job description, and JobPilot builds a
            tailored resume, transparent ATS compatibility estimate, and cover letter.
          </p>
        </section>

        {!result && (
          <section className="builder-card">
            <div className="step-grid">
              <div className="step-card">
                <div className="step-number">01</div>
                <div className="step-title">Upload your resume</div>
                <label className="upload-zone">
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    onChange={(e) => {
                      setResumeFile(e.target.files?.[0] || null);
                      setError("");
                    }}
                  />
                  <div className="upload-icon">↑</div>
                  <strong>{resumeFile ? resumeFile.name : "Choose a PDF or DOCX"}</strong>
                  <span>{resumeFile ? "Ready to analyze" : "Click here or drag your file in"}</span>
                </label>
              </div>

              <div className="step-card">
                <div className="step-number">02</div>
                <div className="step-title">Paste the job description</div>
                <textarea
                  className="job-input"
                  value={jobDescription}
                  onChange={(e) => {
                    setJobDescription(e.target.value);
                    setError("");
                  }}
                  placeholder="Paste the complete job description here..."
                />
                <div className="input-meta">{jobDescription.length.toLocaleString()} characters</div>
              </div>
            </div>

            {error && <div className="error-box">{error}</div>}

            <button
              className={`primary-button ${loading ? "is-loading" : ""}`}
              onClick={buildApplication}
              disabled={!canBuild}
            >
              {loading ? "Building your application..." : "Build My Application"}
              {!loading && <span>→</span>}
            </button>

            {loading && (
              <div className="progress-panel">
                {progress.map((item, index) => (
                  <div className="progress-row" key={item}>
                    <span className="progress-dot">{index === 0 ? "✓" : "•"}</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="privacy-note">
              Your resume is used to create this application. JobPilot does not add
              experience or skills that are not supported by your resume.
            </div>
          </section>
        )}

        {result && (
          <section className="results">
            <div className="results-header">
              <div>
                <div className="eyebrow">APPLICATION READY</div>
                <h2>{job?.job_title || "Target role"}</h2>
                <p>{job?.company || "Company"}{job?.location ? ` · ${job.location}` : ""}</p>
              </div>
              <button className="secondary-button" onClick={() => setResult(null)}>
                ← Start another application
              </button>
            </div>

            <div className="score-layout">
              <div className={`score-card ${scoreClass(ats?.overall_score || 0)}`}>
                <div className="score-label">ATS Compatibility</div>
                <div className="score-number">{ats?.overall_score ?? 0}<span>%</span></div>
                <div className="score-caption">
                  Estimate based on this job description and your tailored resume.
                </div>
              </div>

              <div className="breakdown-card">
                <div className="card-title">What drives the score</div>
                {Object.entries(ats?.breakdown || {}).map(([key, value]) => (
                  <div className="metric" key={key}>
                    <div>
                      <span>{key.replaceAll("_", " ")}</span>
                      <strong>{value}%</strong>
                    </div>
                    <div className="metric-track">
                      <div className="metric-fill" style={{ width: `${value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="result-tabs">
              {[
                ["overview", "Overview"],
                ["resume", "Tailored Resume"],
                ["letter", "Cover Letter"],
              ].map(([id, label]) => (
                <button
                  key={id}
                  className={activeTab === id ? "active" : ""}
                  onClick={() => setActiveTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            {activeTab === "overview" && (
              <div className="overview-grid">
                <div className="result-card">
                  <div className="card-title">Matched skills</div>
                  <div className="tag-list">
                    {(ats?.matched_hard_skills || []).slice(0, 12).map((skill) => (
                      <span className="tag positive" key={skill}>{skill}</span>
                    ))}
                  </div>
                  <div className="card-title gap-title">Skills not demonstrated</div>
                  <div className="tag-list">
                    {(ats?.missing_hard_skills || []).slice(0, 10).map((skill) => (
                      <span className="tag neutral" key={skill}>{skill}</span>
                    ))}
                  </div>
                </div>

                <div className="result-card">
                  <div className="card-title">Next improvements</div>
                  <ul className="improvement-list">
                    {(ats?.improvement_suggestions || []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {activeTab === "resume" && (
              <div className="document-section">
                <div className="document-actions">
                  <div>
                    <div className="card-title">Tailored resume</div>
                    <p>Job-relevant wording is tailored while your factual background is preserved.</p>
                  </div>
                  <button className="primary-small" onClick={downloadResume}>Download DOCX</button>
                </div>

                <ResumePreview resume={resume} />
              </div>
            )}

            {activeTab === "letter" && (
              <div className="document-section">
                <div className="document-actions">
                  <div>
                    <div className="card-title">Cover letter</div>
                    <p>Written from the evidence in your resume and the target role.</p>
                  </div>
                  <button className="primary-small" onClick={downloadCoverLetter}>Download DOCX</button>
                </div>

                <div className="letter-paper">
                  {coverLetter.split("\n\n").map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </div>
            )}

            <div className="estimate-note">
              <strong>About the ATS score:</strong> {ats?.disclaimer}
            </div>
          </section>
        )}
      </main>

      <footer>
        <span>JobPilot AI</span>
        <span>Built for faster, evidence-grounded applications.</span>
      </footer>
    </div>
  );
}

function ResumePreview({ resume }) {
  if (!resume) return null;

  return (
    <div className="resume-paper">
      <div className="resume-name">{resume.name || "Resume"}</div>
      <div className="resume-contact">
        {[resume.email, resume.phone, resume.location, resume.linkedin, resume.github]
          .filter(Boolean)
          .join(" · ")}
      </div>

      {resume.summary && <ResumeSection title="Professional Summary"><p>{resume.summary}</p></ResumeSection>}

      {resume.skills?.length > 0 && (
        <ResumeSection title="Skills">
          <p>{resume.skills.join(", ")}</p>
        </ResumeSection>
      )}

      {resume.experience?.length > 0 && (
        <ResumeSection title="Professional Experience">
          {resume.experience.map((item, index) => (
            <div className="resume-entry" key={`${item.company}-${index}`}>
              <div className="entry-top">
                <strong>{item.title}</strong>
                <span>{item.dates}</span>
              </div>
              <div className="entry-company">
                {[item.company, item.location].filter(Boolean).join(" · ")}
              </div>
              <ul>
                {item.bullets?.map((bullet) => <li key={bullet}>{bullet}</li>)}
              </ul>
            </div>
          ))}
        </ResumeSection>
      )}

      {resume.projects?.length > 0 && (
        <ResumeSection title="Projects">
          {resume.projects.map((item) => (
            <div className="resume-entry" key={item.name}>
              <div className="entry-top"><strong>{item.name}</strong><span>{item.dates}</span></div>
              <ul>{item.bullets?.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
            </div>
          ))}
        </ResumeSection>
      )}

      {resume.education?.length > 0 && (
        <ResumeSection title="Education">
          {resume.education.map((item) => (
            <div className="resume-entry" key={`${item.school}-${item.degree}`}>
              <div className="entry-top"><strong>{item.degree}</strong><span>{item.dates}</span></div>
              <div className="entry-company">{item.school}</div>
              <ul>{item.details?.map((detail) => <li key={detail}>{detail}</li>)}</ul>
            </div>
          ))}
        </ResumeSection>
      )}
    </div>
  );
}

function ResumeSection({ title, children }) {
  return (
    <section className="resume-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export default App;
