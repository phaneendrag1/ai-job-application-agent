import { useMemo, useRef, useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const MAX_FILE_SIZE = 8 * 1024 * 1024;
const MAX_JOB_LENGTH = 30000;


/* =========================================================
   HELPERS
========================================================= */

function displayValue(value, fallback = "—") {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  if (Array.isArray(value)) {
    const result = value
      .map((item) => displayValue(item, ""))
      .filter(Boolean);

    return result.length
      ? result.join(", ")
      : fallback;
  }

  if (typeof value === "object") {
    const keys = [
      "value",
      "display",
      "label",
      "score",
      "match_rate",
      "percentage",
      "rate",
      "count",
      "name",
      "type",
      "status",
      "text",
      "title",
    ];

    for (const key of keys) {
      if (
        value[key] !== undefined &&
        value[key] !== null &&
        value[key] !== ""
      ) {
        return displayValue(
          value[key],
          fallback
        );
      }
    }

    return fallback;
  }

  return fallback;
}


function getScore(ats) {
  if (!ats) {
    return undefined;
  }

  const values = [
    ats.match_rate,
    ats.ats_score,
    ats.overall_score,
  ];

  for (const item of values) {
    const number = Number(
      displayValue(item, "")
    );

    if (!Number.isNaN(number)) {
      return number;
    }
  }

  return undefined;
}


/* =========================================================
   APP
========================================================= */

export default function App() {
  const fileInputRef =
    useRef(null);

  const [
    resumeFile,
    setResumeFile,
  ] = useState(null);

  const [
    jobSource,
    setJobSource,
  ] = useState("description");

  const [
    jobDescription,
    setJobDescription,
  ] = useState("");

  const [
    ashbyUrl,
    setAshbyUrl,
  ] = useState("");

  const [
    baselineAnalysis,
    setBaselineAnalysis,
  ] = useState(null);

  const [
    tailoredResult,
    setTailoredResult,
  ] = useState(null);

  const [
    coverLetter,
    setCoverLetter,
  ] = useState(null);

  const [
    activeTab,
    setActiveTab,
  ] = useState("overview");

  const [
    loadingAction,
    setLoadingAction,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const hasJobInput =
    jobSource === "description"
      ? jobDescription.trim().length > 0
      : ashbyUrl.trim().length > 0;

  const canRun =
    Boolean(
      resumeFile &&
      hasJobInput
    );

  const progress =
    useMemo(() => {
      if (coverLetter) {
        return 100;
      }

      if (tailoredResult) {
        return 90;
      }

      if (baselineAnalysis) {
        return 60;
      }

      if (canRun) {
        return 30;
      }

      if (resumeFile) {
        return 15;
      }

      return 0;
    }, [
      coverLetter,
      tailoredResult,
      baselineAnalysis,
      canRun,
      resumeFile,
    ]);

  const jobIntelligence =
    tailoredResult?.job_intelligence ||
    baselineAnalysis?.job_intelligence ||
    {};

  const analysis =
    tailoredResult?.analysis ||
    baselineAnalysis?.analysis ||
    {};

  const baselineAts =
    tailoredResult?.baseline_ats ||
    baselineAnalysis?.ats ||
    {};

  const tailoredAts =
    tailoredResult?.ats ||
    {};

  const baselineScore =
    tailoredResult?.comparison?.baseline ??
    getScore(baselineAts);

  const tailoredScore =
    tailoredResult?.comparison?.tailored ??
    getScore(tailoredAts);

  const scoreChange =
    tailoredResult?.comparison?.change ??
    (
      baselineScore !== undefined &&
      tailoredScore !== undefined
        ? tailoredScore -
          baselineScore
        : undefined
    );

  const targetRole =
    jobIntelligence.job_title ||
    "Target role";


  /* =======================================================
     FILE
  ======================================================= */

  function validateFile(file) {
    if (!file) {
      return false;
    }

    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setError(
        "Please upload a PDF or DOCX resume."
      );

      return false;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(
        "Your resume must be smaller than 8 MB."
      );

      return false;
    }

    return true;
  }


  function applyFile(file) {
    if (!validateFile(file)) {
      return;
    }

    setError("");
    setResumeFile(file);

    setBaselineAnalysis(null);
    setTailoredResult(null);
    setCoverLetter(null);

    setActiveTab("overview");
  }


  function handleFileChange(event) {
    const file =
      event.target.files?.[0];

    if (file) {
      applyFile(file);
    }
  }


  function handleDrop(event) {
    event.preventDefault();

    const file =
      event.dataTransfer.files?.[0];

    if (file) {
      applyFile(file);
    }
  }


  /* =======================================================
     FORM DATA
  ======================================================= */

  function buildFormData() {
    const formData =
      new FormData();

    formData.append(
      "resume",
      resumeFile
    );

    formData.append(
      "job_description",
      jobSource === "description"
        ? jobDescription.trim()
        : ""
    );

    formData.append(
      "ashby_url",
      jobSource === "ashby"
        ? ashbyUrl.trim()
        : ""
    );

    return formData;
  }


  /* =======================================================
     API
  ======================================================= */

  async function postRequest(
    endpoint
  ) {

    const response =
      await fetch(
        `${API_URL}${endpoint}`,
        {
          method: "POST",
          body: buildFormData(),
        }
      );

    const contentType =
      response.headers.get(
        "content-type"
      ) || "";

    if (!response.ok) {

      if (
        contentType.includes(
          "application/json"
        )
      ) {

        const data =
          await response.json();

        throw new Error(
          data.detail ||
          "Request failed."
        );
      }

      throw new Error(
        `Request failed (${response.status}).`
      );
    }

    return response.json();
  }


  /* =======================================================
     ANALYZE
  ======================================================= */

  async function analyzeJob() {

    if (!canRun) {

      setError(
        "Upload your resume and add a target job first."
      );

      return;
    }

    setError("");
    setLoadingAction("analyze");

    try {

      const data =
        await postRequest(
          "/analyze"
        );

      setBaselineAnalysis(
        data
      );

      setTailoredResult(null);
      setCoverLetter(null);

      setActiveTab(
        "overview"
      );

    } catch (err) {

      setError(
        err.message ||
        "Unable to analyze the job."
      );

    } finally {

      setLoadingAction("");
    }
  }


  /* =======================================================
     TAILOR
  ======================================================= */

  async function tailorResume() {

    if (!canRun) {

      setError(
        "Upload your resume and add a target job first."
      );

      return;
    }

    setError("");
    setLoadingAction("tailor");

    try {

      if (!baselineAnalysis) {

        const baseline =
          await postRequest(
            "/analyze"
          );

        setBaselineAnalysis(
          baseline
        );
      }

      const data =
        await postRequest(
          "/tailor"
        );

      setTailoredResult(
        data
      );

      setActiveTab(
        "ats"
      );

    } catch (err) {

      setError(
        err.message ||
        "Unable to tailor the resume."
      );

    } finally {

      setLoadingAction("");
    }
  }


  /* =======================================================
     COVER LETTER
  ======================================================= */

  async function generateCoverLetter() {

    if (!canRun) {

      setError(
        "Upload your resume and add a target job first."
      );

      return;
    }

    setError("");
    setLoadingAction("cover");

    try {

      const data =
        await postRequest(
          "/cover-letter"
        );

      setCoverLetter(
        data.cover_letter
      );

      setActiveTab(
        "cover"
      );

    } catch (err) {

      setError(
        err.message ||
        "Unable to generate the cover letter."
      );

    } finally {

      setLoadingAction("");
    }
  }


  /* =======================================================
     DOWNLOAD
  ======================================================= */

  async function downloadResume() {

    const resume =
      tailoredResult?.tailored_resume;

    if (!resume) {

      setError(
        "Tailored resume is not available yet."
      );

      return;
    }

    try {

      setError("");

      const response =
        await fetch(
          `${API_URL}/download-resume`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              tailored_resume:
                resume,

              target_role:
                targetRole,
            }),
          }
        );

      if (!response.ok) {

        throw new Error(
          "Unable to download the resume."
        );
      }

      const blob =
        await response.blob();

      downloadBlob(
        blob,
        "tailored-resume.docx"
      );

    } catch (err) {

      setError(
        err.message ||
        "Unable to download the resume."
      );
    }
  }


  async function downloadCoverLetter() {

    if (!coverLetter) {

      setError(
        "Cover letter is not available yet."
      );

      return;
    }

    try {

      setError("");

      const response =
        await fetch(
          `${API_URL}/download-cover-letter`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              cover_letter:
                coverLetter,
            }),
          }
        );

      if (!response.ok) {

        throw new Error(
          "Unable to download the cover letter."
        );
      }

      const blob =
        await response.blob();

      downloadBlob(
        blob,
        "cover-letter.docx"
      );

    } catch (err) {

      setError(
        err.message ||
        "Unable to download the cover letter."
      );
    }
  }


  function downloadBlob(
    blob,
    filename
  ) {

    const url =
      URL.createObjectURL(
        blob
      );

    const link =
      document.createElement(
        "a"
      );

    link.href = url;
    link.download = filename;

    document.body.appendChild(
      link
    );

    link.click();
    link.remove();

    URL.revokeObjectURL(
      url
    );
  }


  /* =======================================================
     RESET
  ======================================================= */

  function resetWorkspace() {

    setResumeFile(null);
    setJobSource("description");

    setJobDescription("");
    setAshbyUrl("");

    setBaselineAnalysis(null);
    setTailoredResult(null);
    setCoverLetter(null);

    setActiveTab("overview");
    setLoadingAction("");
    setError("");

    if (
      fileInputRef.current
    ) {
      fileInputRef.current.value =
        "";
    }
  }


  /* =======================================================
     WORKFLOW
  ======================================================= */

  const steps = [
    {
      number: "01",
      title: "Resume",
      subtitle: "Upload",
      done: Boolean(
        resumeFile
      ),
    },

    {
      number: "02",
      title: "Job",
      subtitle: "Target",
      done: Boolean(
        hasJobInput
      ),
    },

    {
      number: "03",
      title: "Analyze",
      subtitle: "Understand",
      done: Boolean(
        baselineAnalysis
      ),
    },

    {
      number: "04",
      title: "Tailor",
      subtitle: "Optimize",
      done: Boolean(
        tailoredResult
      ),
    },

    {
      number: "05",
      title: "Apply",
      subtitle: "Ready",
      done: Boolean(
        coverLetter
      ),
    },
  ];


  return (
    <div className="app-shell">

      <div className="glow glow-one" />
      <div className="glow glow-two" />


      {/* HEADER */}

      <header className="topbar">

        <div className="topbar-inner">

          <div className="brand">

            <div className="brand-logo">
              ✦
            </div>

            <div className="brand-info">

              <strong>
                JobPilot AI
              </strong>

              <span>
                Intelligent job applications
              </span>

            </div>

          </div>


          <div className="topbar-actions">

            <div className="engine-status">

              <span className="online-dot" />

              AI Engine Online

            </div>


            <button
              type="button"
              className="reset-button"
              onClick={
                resetWorkspace
              }
            >
              Reset Workspace
            </button>

          </div>

        </div>

      </header>


      <main className="main">

        {/* HERO */}

        <section className="hero">

          <div className="hero-content">

            <div className="eyebrow">

              <span>
                ✦
              </span>

              AI JOB APPLICATION WORKSPACE

            </div>


            <h1>

              Build a smarter
              application

              <span>
                {" "}
                for every job.
              </span>

            </h1>


            <p>
              Upload your resume, add a target
              job, and let JobPilot analyze the
              role, tailor your resume, check ATS
              compatibility, and create a focused
              cover letter.
            </p>


            <div className="hero-benefits">

              <span>
                ✓ Verified resume facts
              </span>

              <span>
                ✓ ATS-focused optimization
              </span>

              <span>
                ✓ Job-specific documents
              </span>

            </div>

          </div>


          <aside className="progress-card">

            <div className="progress-card-top">

              <div>

                <div className="progress-label">
                  APPLICATION PROGRESS
                </div>

                <div className="progress-number">
                  {progress}%
                </div>

              </div>

              <div className="progress-star">
                ✦
              </div>

            </div>


            <div className="progress-track">

              <div
                className="progress-fill"
                style={{
                  width:
                    `${progress}%`,
                }}
              />

            </div>


            <div className="progress-status">

              <strong>

                {progress === 100
                  ? "Application ready"
                  : progress >= 90
                  ? "ATS optimization complete"
                  : progress >= 60
                  ? "Job analyzed"
                  : progress >= 30
                  ? "Inputs received"
                  : progress > 0
                  ? "Resume uploaded"
                  : "Ready to begin"}

              </strong>


              <span>

                {progress >= 90
                  ? "Review your ATS score and tailored resume."
                  : "Upload a resume and add a target job."}

              </span>

            </div>

          </aside>

        </section>


        {/* WORKFLOW */}

        <section className="workflow">

          {steps.map(
            (
              step,
              index
            ) => (

              <div
                className="workflow-step"
                key={
                  step.number
                }
              >

                <div
                  className={`workflow-number ${
                    step.done
                      ? "complete"
                      : ""
                  }`}
                >
                  {step.number}
                </div>


                <div className="workflow-text">

                  <strong>
                    {step.title}
                  </strong>

                  <span>
                    {step.subtitle}
                  </span>

                </div>


                {index <
                  steps.length -
                    1 && (
                  <div className="workflow-line" />
                )}

              </div>

            )
          )}

        </section>


        {/* BUILDER */}

        <section className="builder-section">

          <div className="section-heading">

            <div>

              <div className="section-label">
                APPLICATION BUILDER
              </div>

              <h2>
                Prepare your application
              </h2>

              <p>
                Start with your resume and one
                specific target job posting.
              </p>

            </div>


            <div className="waiting-badge">

              <span className="online-dot" />

              {canRun
                ? "Ready"
                : "Waiting for input"}

            </div>

          </div>


          <div className="builder-grid">

            {/* RESUME CARD */}

            <article className="builder-card">

              <div className="card-heading">

                <div>

                  <div className="card-step">
                    01 · RESUME
                  </div>

                  <h3>
                    Your Resume
                  </h3>

                </div>


                <span
                  className={`status-label ${
                    resumeFile
                      ? "ready"
                      : ""
                  }`}
                >
                  {resumeFile
                    ? "READY"
                    : "REQUIRED"}
                </span>

              </div>


              <div
                className={`upload-zone ${
                  resumeFile
                    ? "selected"
                    : ""
                }`}
                onDragOver={(event) =>
                  event.preventDefault()
                }
                onDrop={
                  handleDrop
                }
                onClick={() =>
                  fileInputRef.current?.click()
                }
              >

                <input
                  ref={
                    fileInputRef
                  }
                  type="file"
                  accept=".pdf,.docx"
                  hidden
                  onChange={
                    handleFileChange
                  }
                />


                <div className="upload-icon">
                  {resumeFile
                    ? "✓"
                    : "↑"}
                </div>


                <h4>
                  {resumeFile
                    ? resumeFile.name
                    : "Drop your resume here"}
                </h4>


                <p>
                  {resumeFile
                    ? `${(
                        resumeFile.size /
                        (1024 * 1024)
                      ).toFixed(
                        2
                      )} MB · Ready to process`
                    : "or click to browse"}
                </p>


                {!resumeFile && (

                  <>

                    <div className="file-types">

                      <span>
                        PDF
                      </span>

                      <span>
                        DOCX
                      </span>

                    </div>

                    <small>
                      Maximum file size: 8 MB
                    </small>

                  </>

                )}


                {resumeFile && (

                  <button
                    type="button"
                    className="change-file"
                    onClick={(event) => {

                      event.stopPropagation();

                      fileInputRef.current?.click();

                    }}
                  >
                    Change file
                  </button>

                )}

              </div>

            </article>


            {/* JOB CARD */}

            <article className="builder-card">

              <div className="card-heading">

                <div>

                  <div className="card-step">
                    02 · TARGET JOB
                  </div>

                  <h3>
                    Target Job
                  </h3>

                </div>


                <span
                  className={`status-label ${
                    hasJobInput
                      ? "ready"
                      : ""
                  }`}
                >
                  {hasJobInput
                    ? "READY"
                    : "REQUIRED"}
                </span>

              </div>


              <div className="source-tabs">

                <button
                  type="button"
                  className={
                    jobSource ===
                    "description"
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setJobSource(
                      "description"
                    )
                  }
                >
                  Job Description
                </button>


                <button
                  type="button"
                  className={
                    jobSource ===
                    "ashby"
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setJobSource(
                      "ashby"
                    )
                  }
                >
                  Ashby URL
                </button>

              </div>


              {jobSource ===
              "description" ? (

                <>

                  <textarea
                    value={
                      jobDescription
                    }
                    maxLength={
                      MAX_JOB_LENGTH
                    }
                    onChange={(event) =>
                      setJobDescription(
                        event.target.value
                      )
                    }
                    placeholder={`Paste one specific job description here...

Job title
Responsibilities
Required skills
Experience
Qualifications`}
                  />


                  <div className="textarea-footer">

                    <span>
                      One specific posting gives
                      the best results.
                    </span>

                    <strong>
                      {
                        jobDescription.length.toLocaleString()
                      }
                      /30,000
                    </strong>

                  </div>

                </>

              ) : (

                <div className="ashby-panel">

                  <div className="ashby-icon">
                    ↗
                  </div>


                  <div className="ashby-content">

                    <label htmlFor="ashby-url">
                      Ashby job posting URL
                    </label>


                    <input
                      id="ashby-url"
                      type="url"
                      value={
                        ashbyUrl
                      }
                      onChange={(event) =>
                        setAshbyUrl(
                          event.target.value
                        )
                      }
                      placeholder="https://jobs.ashbyhq.com/company/..."
                    />


                    <p>
                      JobPilot retrieves the public
                      posting automatically.
                    </p>

                  </div>

                </div>

              )}

            </article>

          </div>


          {error && (

            <div className="error-box">

              <strong>
                !
              </strong>

              <span>
                {error}
              </span>

            </div>

          )}

        </section>


        {/* ACTIONS */}

        <section className="actions-section">

          <div className="section-label">
            ✦ AI ACTIONS
          </div>


          <p className="actions-description">
            Analyze the job, tailor your resume,
            automatically optimize ATS compatibility,
            and generate your cover letter.
          </p>


          <div className="action-grid">

            <ActionCard
              number="01"
              icon="◉"
              title="Analyze Job"
              description="Understand requirements, skills, experience, responsibilities, and keywords."
              buttonText={
                loadingAction ===
                "analyze"
                  ? "Analyzing..."
                  : "Analyze Job"
              }
              onClick={
                analyzeJob
              }
              disabled={
                !canRun ||
                loadingAction !==
                  ""
              }
            />


            <ActionCard
              number="02"
              icon="✦"
              title="Tailor Resume"
              description="Create a job-specific resume and automatically optimize it through multiple ATS checks."
              buttonText={
                loadingAction ===
                "tailor"
                  ? "Optimizing..."
                  : "Tailor My Resume"
              }
              onClick={
                tailorResume
              }
              disabled={
                !canRun ||
                loadingAction !==
                  ""
              }
              featured
            />


            <ActionCard
              number="03"
              icon="✉"
              title="Cover Letter"
              description="Generate a focused cover letter connecting your verified background to the target role."
              buttonText={
                loadingAction ===
                "cover"
                  ? "Generating..."
                  : "Generate Cover Letter"
              }
              onClick={
                generateCoverLetter
              }
              disabled={
                !canRun ||
                loadingAction !==
                  ""
              }
            />

          </div>


          {tailoredResult && (

            <div className="ats-auto-notice">

              <div className="ats-notice-icon">
                ✓
              </div>


              <div>

                <strong>
                  Automatic ATS optimization complete
                </strong>

                <p>
                  JobPilot tested the tailored resume
                  against the target job requirements.
                </p>

              </div>


              <button
                type="button"
                onClick={() =>
                  setActiveTab(
                    "ats"
                  )
                }
              >
                View ATS Score →
              </button>

            </div>

          )}

        </section>


        {/* RESULTS */}

        {(baselineAnalysis ||
          tailoredResult ||
          coverLetter) && (

          <section className="results-section">

            <div className="section-heading">

              <div>

                <div className="section-label">
                  RESULTS
                </div>

                <h2>
                  Application intelligence
                </h2>

                <p>
                  Review job analysis, ATS results,
                  and generated application documents.
                </p>

              </div>


              <div className="role-card">

                <span>
                  TARGET ROLE
                </span>

                <strong>
                  {targetRole}
                </strong>

              </div>

            </div>


            <div className="result-tabs">

              <button
                type="button"
                className={
                  activeTab ===
                  "overview"
                    ? "active"
                    : ""
                }
                onClick={() =>
                  setActiveTab(
                    "overview"
                  )
                }
              >
                Overview
              </button>


              <button
                type="button"
                className={
                  activeTab ===
                  "ats"
                    ? "active"
                    : ""
                }
                disabled={
                  !tailoredResult &&
                  !baselineAnalysis
                }
                onClick={() =>
                  setActiveTab(
                    "ats"
                  )
                }
              >
                ATS Score
              </button>


              <button
                type="button"
                className={
                  activeTab ===
                  "resume"
                    ? "active"
                    : ""
                }
                disabled={
                  !tailoredResult
                }
                onClick={() =>
                  setActiveTab(
                    "resume"
                  )
                }
              >
                Tailored Resume
              </button>


              <button
                type="button"
                className={
                  activeTab ===
                  "cover"
                    ? "active"
                    : ""
                }
                disabled={
                  !coverLetter
                }
                onClick={() =>
                  setActiveTab(
                    "cover"
                  )
                }
              >
                Cover Letter
              </button>

            </div>


            {/* OVERVIEW */}

            {activeTab ===
              "overview" && (

              <div className="result-content">

                <div className="stats-grid">

                  <Stat
                    value={
                      tailoredScore ??
                      baselineScore ??
                      "—"
                    }
                    label="ATS score"
                    primary
                  />

                  <Stat
                    value={
                      jobIntelligence
                        .hard_skills
                        ?.length ||
                      0
                    }
                    label="Hard skills"
                  />

                  <Stat
                    value={
                      jobIntelligence
                        .soft_skills
                        ?.length ||
                      0
                    }
                    label="Soft skills"
                  />

                  <Stat
                    value={
                      jobIntelligence
                        .keywords
                        ?.length ||
                      0
                    }
                    label="Keywords"
                  />

                </div>


                <div className="results-grid">

                  <ResultCard
                    title="Hard Skills"
                    label="ROLE INTELLIGENCE"
                  >

                    <TagList
                      items={
                        jobIntelligence.hard_skills
                      }
                      limit={14}
                    />

                  </ResultCard>


                  <ResultCard
                    title="Soft Skills"
                    label="ROLE INTELLIGENCE"
                  >

                    <TagList
                      items={
                        jobIntelligence.soft_skills
                      }
                      limit={10}
                    />

                  </ResultCard>

                </div>


                <div className="results-grid">

                  <ResultCard
                    title="Keywords"
                    label="SEARCH & ATS"
                  >

                    <TagList
                      items={
                        jobIntelligence.keywords
                      }
                      limit={18}
                    />

                  </ResultCard>


                  <ResultCard
                    title="Responsibilities"
                    label="TARGET ROLE"
                  >

                    <div className="insight-list">

                      {(
                        jobIntelligence.responsibilities ||
                        []
                      )
                        .slice(
                          0,
                          8
                        )
                        .map(
                          (
                            item,
                            index
                          ) => (

                            <div
                              className="insight-item"
                              key={
                                index
                              }
                            >

                              <span>
                                {String(
                                  index +
                                    1
                                ).padStart(
                                  2,
                                  "0"
                                )}
                              </span>

                              <p>
                                {displayValue(
                                  item
                                )}
                              </p>

                            </div>

                          )
                        )}

                    </div>

                  </ResultCard>

                </div>


                {analysis.summary && (

                  <ResultCard
                    title="Resume Match Summary"
                    label="AI ANALYSIS"
                  >

                    <p className="large-copy">
                      {displayValue(
                        analysis.summary,
                        ""
                      )}
                    </p>

                  </ResultCard>

                )}

              </div>

            )}


            {/* ATS */}

            {activeTab ===
              "ats" && (

              <div className="result-content">

                <div className="ats-score-hero">

                  <div className="ats-score-main">

                    <div className="ats-score-copy">

                      <div className="small-label">
                        AUTOMATIC ATS OPTIMIZATION
                      </div>

                      <h3>
                        Tailored resume ATS score
                      </h3>

                      <p>
                        JobPilot scores hard skills,
                        keywords, experience alignment,
                        exact title visibility,
                        searchability, measurable
                        results, and resume structure.
                      </p>

                    </div>


                    <div className="ats-score-circle">

                      <strong>
                        {tailoredScore ??
                          baselineScore ??
                          "—"}
                      </strong>

                      <span>
                        / 100
                      </span>

                    </div>

                  </div>


                  <div className="ats-target-status">

                    <div>

                      <span>
                        TARGET
                      </span>

                      <strong>
                        90+
                      </strong>

                    </div>


                    <div>

                      <span>
                        CURRENT
                      </span>

                      <strong>
                        {tailoredScore ??
                          baselineScore ??
                          "—"}
                      </strong>

                    </div>


                    <div>

                      <span>
                        STATUS
                      </span>

                      <strong
                        className={
                          tailoredResult
                            ? tailoredScore >= 90
                              ? "ats-target-good"
                              : "ats-target-review"
                            : "ats-target-review"
                        }
                      >
                        {tailoredResult
                          ? tailoredScore >=
                            90
                            ? "Target reached"
                            : "Further improvement possible"
                          : "Tailor resume to optimize"}
                      </strong>

                    </div>

                  </div>


                  <div className="ats-comparison">

                    <div className="ats-comparison-card">

                      <span>
                        BASELINE
                      </span>

                      <strong>
                        {baselineScore !==
                        undefined
                          ? `${baselineScore}/100`
                          : "—"}
                      </strong>

                      <small>
                        Original resume
                      </small>

                    </div>


                    <div className="ats-comparison-arrow">
                      →
                    </div>


                    <div className="ats-comparison-card improved">

                      <span>
                        TAILORED
                      </span>

                      <strong>
                        {tailoredScore !==
                        undefined
                          ? `${tailoredScore}/100`
                          : "—"}
                      </strong>

                      <small>
                        Optimized resume
                      </small>

                    </div>


                    <div
                      className={`ats-change ${
                        scoreChange !==
                          undefined &&
                        scoreChange < 0
                          ? "negative"
                          : "positive"
                      }`}
                    >
                      {scoreChange !==
                      undefined
                        ? `${scoreChange >= 0 ? "+" : ""}${scoreChange} points`
                        : "No comparison"}
                    </div>

                  </div>

                </div>


                {tailoredResult && (

                  <div className="optimization-banner">

                    <div className="optimization-icon">
                      ✦
                    </div>

                    <div>

                      <strong>
                        ATS optimization completed
                      </strong>

                      <p>
                        JobPilot tested multiple
                        resume versions and kept
                        the strongest scoring version.
                      </p>

                    </div>

                    <div className="optimization-rounds">

                      <span>
                        ROUNDS
                      </span>

                      <strong>
                        {
                          tailoredAts
                            .optimization_rounds ??
                          1
                        }
                      </strong>

                    </div>

                  </div>

                )}


                <div className="ats-metrics">

                  <AtsMetric
                    label="Hard skills"
                    value={
                      tailoredAts.hard_skills_match ||
                      baselineAts.hard_skills_match ||
                      "0/0"
                    }
                  />

                  <AtsMetric
                    label="Soft skills"
                    value={
                      tailoredAts.soft_skills_match ||
                      baselineAts.soft_skills_match ||
                      "0/0"
                    }
                  />

                  <AtsMetric
                    label="Keywords"
                    value={
                      tailoredAts.keyword_match ||
                      baselineAts.keyword_match ||
                      "0/0"
                    }
                  />

                  <AtsMetric
                    label="Experience"
                    value={
                      tailoredAts.experience_match ||
                      baselineAts.experience_match ||
                      "0/0"
                    }
                  />

                  <AtsMetric
                    label="Measured results"
                    value={
                      tailoredAts.measurable_results_count ??
                      baselineAts.measurable_results_count ??
                      0
                    }
                  />

                  <AtsMetric
                    label="Searchability"
                    value={
                      tailoredAts.searchability_score !==
                      undefined
                        ? `${tailoredAts.searchability_score}%`
                        : baselineAts.searchability_score !==
                          undefined
                        ? `${baselineAts.searchability_score}%`
                        : "—"
                    }
                  />

                  <AtsMetric
                    label="Word count"
                    value={
                      tailoredAts.word_count ??
                      baselineAts.word_count ??
                      "—"
                    }
                  />

                  <AtsMetric
                    label="Formatting"
                    value={
                      tailoredAts.formatting_score !==
                      undefined
                        ? `${tailoredAts.formatting_score}%`
                        : baselineAts.formatting_score !==
                          undefined
                        ? `${baselineAts.formatting_score}%`
                        : "—"
                    }
                  />

                </div>


                {tailoredResult ? (

                  <>

                    <ResultCard
                      title="Matched Hard Skills"
                      label="TAILORED RESUME"
                    >

                      <TagList
                        items={
                          tailoredAts.matched_hard_skills
                        }
                        limit={14}
                      />

                    </ResultCard>


                    <ResultCard
                      title="Hard Skills Still Missing"
                      label="REQUIRES ATTENTION"
                    >

                      <TagList
                        items={
                          tailoredAts.missing_hard_skills
                        }
                        limit={14}
                      />

                    </ResultCard>


                    <ResultCard
                      title="Matched Keywords"
                      label="SEARCH & ATS"
                    >

                      <TagList
                        items={
                          tailoredAts.matched_keywords
                        }
                        limit={18}
                      />

                    </ResultCard>


                    <ResultCard
                      title="Keywords Still Missing"
                      label="SEARCH & ATS"
                    >

                      <TagList
                        items={
                          tailoredAts.missing_keywords
                        }
                        limit={18}
                      />

                    </ResultCard>


                    <ResultCard
                      title="Matched Soft Skills"
                      label="TAILORED RESUME"
                    >

                      <TagList
                        items={
                          tailoredAts.matched_soft_skills
                        }
                        limit={10}
                      />

                    </ResultCard>


                    <ResultCard
                      title="Experience Alignment"
                      label="TARGET ROLE"
                    >

                      <TagList
                        items={
                          tailoredAts.matched_experience
                        }
                        limit={8}
                      />

                      {(
                        tailoredAts
                          .missing_experience
                          ?.length >
                        0
                      ) && (

                        <>

                          <div className="sub-result-title">
                            Still missing
                          </div>

                          <TagList
                            items={
                              tailoredAts
                                .missing_experience
                            }
                            limit={8}
                          />

                        </>

                      )}

                    </ResultCard>

                  </>

                ) : (

                  <ResultCard
                    title="ATS Baseline"
                    label="ORIGINAL RESUME"
                  >

                    <p className="large-copy">
                      Run <strong>Tailor Resume</strong>{" "}
                      to generate the optimized ATS
                      score and before/after comparison.
                    </p>

                  </ResultCard>

                )}


                <ResultCard
                  title="ATS Audit"
                  label="RESUME CHECK"
                >

                  <div className="audit-grid">

                    <AuditItem
                      label="Target title"
                      value={
                        tailoredAts.job_title_status ||
                        baselineAts.job_title_status ||
                        "Review"
                      }
                    />

                    <AuditItem
                      label="Hard skills"
                      value={
                        tailoredAts.hard_skills_match ||
                        baselineAts.hard_skills_match ||
                        "0/0"
                      }
                    />

                    <AuditItem
                      label="Soft skills"
                      value={
                        tailoredAts.soft_skills_match ||
                        baselineAts.soft_skills_match ||
                        "0/0"
                      }
                    />

                    <AuditItem
                      label="Keywords"
                      value={
                        tailoredAts.keyword_match ||
                        baselineAts.keyword_match ||
                        "0/0"
                      }
                    />

                    <AuditItem
                      label="Experience"
                      value={
                        tailoredAts.experience_match ||
                        baselineAts.experience_match ||
                        "0/0"
                      }
                    />

                    <AuditItem
                      label="Measured results"
                      value={
                        tailoredAts.measurable_results_count ??
                        baselineAts.measurable_results_count ??
                        0
                      }
                    />

                    <AuditItem
                      label="Searchability"
                      value={
                        tailoredAts.searchability_score !==
                        undefined
                          ? `${tailoredAts.searchability_score}%`
                          : baselineAts.searchability_score !==
                            undefined
                          ? `${baselineAts.searchability_score}%`
                          : "—"
                      }
                    />

                    <AuditItem
                      label="Date formatting"
                      value={
                        (
                          tailoredAts.date_formatting ??
                          baselineAts.date_formatting
                        )
                          ? "Passed"
                          : "Review"
                      }
                    />

                    <AuditItem
                      label="Word count"
                      value={
                        tailoredAts.word_count ??
                        baselineAts.word_count ??
                        "—"
                      }
                    />

                    <AuditItem
                      label="File type"
                      value={
                        displayValue(
                          tailoredAts.file_type ||
                          baselineAts.file_type,
                          "DOCX"
                        )
                      }
                    />

                    <AuditItem
                      label="Filename"
                      value={
                        displayValue(
                          tailoredAts.filename ||
                          baselineAts.filename,
                          "Available"
                        )
                      }
                    />

                    <AuditItem
                      label="Sections"
                      value={
                        tailoredAts.section_score !==
                        undefined
                          ? `${tailoredAts.section_score}%`
                          : baselineAts.section_score !==
                            undefined
                          ? `${baselineAts.section_score}%`
                          : "—"
                      }
                    />

                  </div>

                </ResultCard>


                {analysis.experience_comparison && (

                  <ResultCard
                    title="Experience Comparison"
                    label="REQUIREMENT ALIGNMENT"
                  >

                    <p className="large-copy">
                      {displayValue(
                        analysis.experience_comparison,
                        ""
                      )}
                    </p>

                  </ResultCard>

                )}


                {analysis.education_comparison && (

                  <ResultCard
                    title="Education Comparison"
                    label="QUALIFICATION ALIGNMENT"
                  >

                    <p className="large-copy">
                      {displayValue(
                        analysis.education_comparison,
                        ""
                      )}
                    </p>

                  </ResultCard>

                )}


                <div className="ats-next-action">

                  <div>

                    <strong>
                      {tailoredResult
                        ? "Tailored resume ready"
                        : "Baseline ATS available"}
                    </strong>

                    <p>
                      {tailoredResult
                        ? "Review the findings and download your optimized resume."
                        : "Tailor the resume to start automatic ATS optimization."}
                    </p>

                  </div>


                  <div className="ats-next-buttons">

                    {tailoredResult && (

                      <button
                        type="button"
                        className="secondary-action"
                        onClick={() =>
                          setActiveTab(
                            "resume"
                          )
                        }
                      >
                        View Resume
                      </button>

                    )}


                    {tailoredResult && (

                      <button
                        type="button"
                        className="primary-action"
                        onClick={
                          downloadResume
                        }
                      >
                        Download DOCX
                      </button>

                    )}

                  </div>

                </div>

              </div>

            )}


            {/* RESUME */}

            {activeTab ===
              "resume" &&
              tailoredResult && (

              <div className="result-content">

                <ResultCard
                  title="Tailored Resume"
                  label="GENERATED DOCUMENT"
                  right={
                    <button
                      type="button"
                      className="download-button"
                      onClick={
                        downloadResume
                      }
                    >
                      Download DOCX
                    </button>
                  }
                >

                  <div className="document-frame">

                    <ResumePreview
                      data={
                        tailoredResult.tailored_resume
                      }
                    />

                  </div>

                </ResultCard>

              </div>

            )}


            {/* COVER */}

            {activeTab ===
              "cover" &&
              coverLetter && (

              <div className="result-content">

                <ResultCard
                  title="Focused Cover Letter"
                  label="GENERATED DOCUMENT"
                  right={
                    <button
                      type="button"
                      className="download-button"
                      onClick={
                        downloadCoverLetter
                      }
                    >
                      Download DOCX
                    </button>
                  }
                >

                  <div className="document-frame">

                    <pre className="cover-preview">
                      {formatCoverLetter(
                        coverLetter
                      )}
                    </pre>

                  </div>

                </ResultCard>

              </div>

            )}

          </section>

        )}

      </main>


      <footer className="footer">

        <div className="footer-inner">

          <div>

            <strong>
              JobPilot AI
            </strong>

            <span>
              Intelligent job application workspace
            </span>

          </div>


          <div className="footer-status">

            <span className="online-dot" />

            Systems operational

          </div>

        </div>

      </footer>

    </div>
  );
}


/* =========================================================
   COMPONENTS
========================================================= */

function ActionCard({
  number,
  icon,
  title,
  description,
  buttonText,
  onClick,
  disabled,
  featured,
}) {
  return (
    <article
      className={`action-card ${
        featured
          ? "featured"
          : ""
      }`}
    >

      <div className="action-top">

        <span>
          {number}
        </span>

        <div>
          {icon}
        </div>

      </div>


      <div className="action-body">

        <div className="action-title-row">

          <h3>
            {title}
          </h3>

          {featured && (

            <span className="recommended">
              Recommended
            </span>

          )}

        </div>


        <p>
          {description}
        </p>

      </div>


      <button
        type="button"
        className="action-button"
        onClick={onClick}
        disabled={disabled}
      >

        <span>
          {buttonText}
        </span>

        <b>
          →
        </b>

      </button>

    </article>
  );
}


function Stat({
  value,
  label,
  primary = false,
}) {
  return (
    <div
      className={`stat-card ${
        primary
          ? "primary"
          : ""
      }`}
    >

      <strong>
        {value}
      </strong>

      <span>
        {label}
      </span>

    </div>
  );
}


function AtsMetric({
  label,
  value,
}) {
  return (
    <div className="ats-metric">

      <span>
        {label}
      </span>

      <strong>
        {displayValue(
          value
        )}
      </strong>

    </div>
  );
}


function ResultCard({
  title,
  label,
  right,
  children,
}) {
  return (
    <article className="result-card">

      <div className="result-card-header">

        <div>

          <div className="small-label">
            {label}
          </div>

          <h3>
            {title}
          </h3>

        </div>

        {right}

      </div>


      {children}

    </article>
  );
}


function AuditItem({
  label,
  value,
}) {
  return (
    <div className="audit-item">

      <span>
        {label}
      </span>

      <strong>
        {displayValue(
          value
        )}
      </strong>

    </div>
  );
}


function TagList({
  items = [],
  limit = 10,
}) {
  const [
    expanded,
    setExpanded,
  ] = useState(false);

  const cleanItems =
    Array.isArray(items)
      ? items.filter(
          (item) =>
            displayValue(
              item,
              ""
            ).trim()
        )
      : [];

  if (!cleanItems.length) {

    return (
      <div className="empty">
        No items found.
      </div>
    );
  }

  const visible =
    expanded
      ? cleanItems
      : cleanItems.slice(
          0,
          limit
        );

  return (
    <>

      <div className="tags">

        {visible.map(
          (
            item,
            index
          ) => (

            <span
              className="tag"
              key={
                index
              }
            >
              {displayValue(
                item,
                ""
              )}
            </span>

          )
        )}

      </div>


      {cleanItems.length >
        limit && (

        <button
          type="button"
          className="show-more"
          onClick={() =>
            setExpanded(
              (value) =>
                !value
            )
          }
        >
          {expanded
            ? "Show less"
            : `Show ${
                cleanItems.length -
                limit
              } more`}
        </button>

      )}

    </>
  );
}


function ResumePreview({
  data,
}) {
  if (!data) {

    return (
      <div className="empty">
        Resume content unavailable.
      </div>
    );
  }

  const contact = [
    data.location,
    data.email,
    data.phone,
    data.linkedin,
    data.github,
  ].filter(Boolean);

  return (
    <div className="resume-page">

      <h1>
        {data.name ||
          "Candidate Name"}
      </h1>


      {contact.length >
        0 && (

        <div className="resume-contact">
          {contact.join(
            " • "
          )}
        </div>

      )}


      {data.summary && (

        <>
          <h2>
            PROFESSIONAL SUMMARY
          </h2>

          <p>
            {displayValue(
              data.summary,
              ""
            )}
          </p>
        </>

      )}


      {Array.isArray(
        data.skills
      ) &&
        data.skills.length >
          0 && (

          <>
            <h2>
              TECHNICAL SKILLS
            </h2>

            <p>
              {data.skills.join(
                ", "
              )}
            </p>
          </>

        )}


      {Array.isArray(
        data.experience
      ) &&
        data.experience.length >
          0 && (

          <>
            <h2>
              PROFESSIONAL EXPERIENCE
            </h2>


            {data.experience.map(
              (
                job,
                index
              ) => (

                <div
                  className="resume-entry"
                  key={
                    index
                  }
                >

                  <div className="resume-row">

                    <strong>
                      {job.title ||
                        ""}
                    </strong>

                    <span>
                      {job.dates ||
                        ""}
                    </span>

                  </div>


                  <div className="resume-company">

                    {job.company ||
                      ""}

                    {job.location
                      ? ` | ${job.location}`
                      : ""}

                  </div>


                  <ul>

                    {(job.bullets ||
                      []
                    ).map(
                      (
                        bullet,
                        bulletIndex
                      ) => (

                        <li
                          key={
                            bulletIndex
                          }
                        >
                          {displayValue(
                            bullet,
                            ""
                          )}
                        </li>

                      )
                    )}

                  </ul>

                </div>

              )
            )}

          </>

        )}


      {Array.isArray(
        data.projects
      ) &&
        data.projects.length >
          0 && (

          <>
            <h2>
              PROJECTS
            </h2>


            {data.projects.map(
              (
                project,
                index
              ) => (

                <div
                  className="resume-entry"
                  key={
                    index
                  }
                >

                  <div className="resume-row">

                    <strong>
                      {project.name ||
                        ""}
                    </strong>

                  </div>


                  {project.technologies?.length >
                    0 && (

                    <div className="resume-company">
                      {
                        project.technologies.join(
                          ", "
                        )
                      }
                    </div>

                  )}


                  {project.description && (

                    <p>
                      {project.description}
                    </p>

                  )}


                  <ul>

                    {(project.bullets ||
                      []
                    ).map(
                      (
                        bullet,
                        bulletIndex
                      ) => (

                        <li
                          key={
                            bulletIndex
                          }
                        >
                          {displayValue(
                            bullet,
                            ""
                          )}
                        </li>

                      )
                    )}

                  </ul>

                </div>

              )
            )}

          </>

        )}


      {Array.isArray(
        data.education
      ) &&
        data.education.length >
          0 && (

          <>
            <h2>
              EDUCATION
            </h2>


            {data.education.map(
              (
                item,
                index
              ) => (

                <div
                  className="resume-entry"
                  key={
                    index
                  }
                >

                  <div className="resume-row">

                    <strong>
                      {item.degree ||
                        ""}
                    </strong>

                    <span>
                      {item.dates ||
                        ""}
                    </span>

                  </div>


                  <div className="resume-company">
                    {item.institution ||
                      ""}
                  </div>

                </div>

              )
            )}

          </>

        )}

    </div>
  );
}


function formatCoverLetter(
  value
) {
  if (!value) {
    return "";
  }

  if (
    typeof value ===
    "string"
  ) {
    return value;
  }

  const parts = [];

  if (value.date) {
    parts.push(
      displayValue(
        value.date,
        ""
      )
    );
  }

  parts.push(
    displayValue(
      value.salutation ||
      "Dear Hiring Manager,",
      ""
    )
  );

  if (value.opening) {

    parts.push(
      displayValue(
        value.opening,
        ""
      )
    );
  }

  if (
    Array.isArray(
      value.body_paragraphs
    )
  ) {

    value.body_paragraphs.forEach(
      (paragraph) => {

        parts.push(
          displayValue(
            paragraph,
            ""
          )
        );

      }
    );
  }

  parts.push(
    displayValue(
      value.closing ||
      "Kind regards,",
      ""
    )
  );

  if (value.signature) {

    parts.push(
      displayValue(
        value.signature,
        ""
      )
    );
  }

  return parts
    .filter(Boolean)
    .join("\n\n");
}function AtsSuggestions({
  suggestions = [],
}) {
  const [
    showAll,
    setShowAll,
  ] = useState(false);

  const visible =
    showAll
      ? suggestions
      : suggestions.slice(
          0,
          12
        );

  const matched =
    suggestions.filter(
      (item) =>
        item.type ===
        "matched"
    ).length;

  const missing =
    suggestions.filter(
      (item) =>
        item.type ===
        "missing"
    ).length;

  const improvements =
    suggestions.filter(
      (item) =>
        item.type ===
        "improvement"
    ).length;

  return (
    <ResultCard
      title="ATS Improvement Suggestions"
      label="JOBSCAN-STYLE REVIEW"
    >

      <div className="suggestion-summary">

        <div className="suggestion-summary-card matched">

          <span>
            MATCHED
          </span>

          <strong>
            {matched}
          </strong>

        </div>


        <div className="suggestion-summary-card missing">

          <span>
            MISSING
          </span>

          <strong>
            {missing}
          </strong>

        </div>


        <div className="suggestion-summary-card improve">

          <span>
            IMPROVE
          </span>

          <strong>
            {improvements}
          </strong>

        </div>

      </div>


      <div className="suggestion-list">

        {visible.map(
          (
            suggestion,
            index
          ) => (

            <div
              className={`suggestion ${
                suggestion.type
              }`}
              key={
                `${suggestion.category}-${suggestion.item}-${index}`
              }
            >

              <div className="suggestion-icon">

                {suggestion.type ===
                "matched"
                  ? "✓"
                  : suggestion.type ===
                    "missing"
                  ? "!"
                  : "→"}

              </div>


              <div className="suggestion-content">

                <div className="suggestion-heading">

                  <span className="suggestion-category">
                    {displayValue(
                      suggestion.category
                    )}
                  </span>

                  <strong>
                    {displayValue(
                      suggestion.item
                    )}
                  </strong>

                  <span className="suggestion-status">
                    {displayValue(
                      suggestion.status
                    )}
                  </span>

                </div>


                <p>
                  {displayValue(
                    suggestion.message
                  )}
                </p>

              </div>

            </div>

          )
        )}

      </div>


      {suggestions.length >
        12 && (

        <button
          type="button"
          className="show-more suggestions-more"
          onClick={() =>
            setShowAll(
              (value) =>
                !value
            )
          }
        >
          {showAll
            ? "Show fewer suggestions"
            : `Show ${
                suggestions.length -
                12
              } more suggestions`}
        </button>

      )}

    </ResultCard>
  );
}