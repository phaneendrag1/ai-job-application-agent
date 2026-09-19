import { useMemo, useState } from "react";

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");


/* =========================================================
   GENERAL HELPERS
   ========================================================= */

function safeString(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
}


function safeArray(value) {
  return Array.isArray(value) ? value : [];
}


async function parseErrorResponse(response) {
  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes("application/json")
  ) {
    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail ||
        data.message ||
        "The request failed."
      );
    }

    return data;
  }

  const text = await response.text();

  if (!response.ok) {
    throw new Error(
      text ||
      "The request failed."
    );
  }

  try {
    return JSON.parse(text);
  } catch {
    return {
      data: text,
    };
  }
}


/* =========================================================
   RESUME NORMALIZATION
   ========================================================= */

function normalizeSkills(skills) {
  const source =
    skills &&
    typeof skills === "object"
      ? skills
      : {};

  const categories = [
    "Programming",
    "AI / LLM",
    "Machine Learning",
    "Backend / APIs",
    "Databases / Infrastructure",
    "Testing / Delivery",
  ];

  const result = {};

  for (const category of categories) {
    const value = source[category];

    if (Array.isArray(value)) {
      result[category] = value
        .map(safeString)
        .filter(Boolean);
    } else if (typeof value === "string") {
      result[category] = value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    } else {
      result[category] = [];
    }
  }

  return result;
}


function normalizeExperience(experience) {
  return safeArray(experience)
    .map((item) => ({
      title: safeString(item?.title),
      company: safeString(item?.company),
      location: safeString(item?.location),
      dates: safeString(item?.dates),
      bullets: safeArray(item?.bullets)
        .map(safeString)
        .filter(Boolean),
    }))
    .filter(
      (item) =>
        item.title ||
        item.company ||
        item.location ||
        item.dates ||
        item.bullets.length
    );
}


function normalizeProjects(projects) {
  return safeArray(projects)
    .map((item) => ({
      title: safeString(item?.title),
      technologies: safeArray(
        item?.technologies
      )
        .map(safeString)
        .filter(Boolean),
      bullets: safeArray(item?.bullets)
        .map(safeString)
        .filter(Boolean),
    }))
    .filter(
      (item) =>
        item.title ||
        item.technologies.length ||
        item.bullets.length
    );
}


function normalizeEducation(education) {
  return safeArray(education)
    .map((item) => ({
      degree: safeString(item?.degree),
      institution: safeString(
        item?.institution
      ),
      location: safeString(item?.location),
      dates: safeString(item?.dates),
    }))
    .filter(
      (item) =>
        item.degree ||
        item.institution ||
        item.location ||
        item.dates
    );
}


function normalizeResume(resume) {
  const source =
    resume &&
    typeof resume === "object"
      ? resume
      : {};

  return {
    name: safeString(source.name),
    location: safeString(
      source.location
    ),
    email: safeString(source.email),
    phone: safeString(source.phone),
    linkedin: safeString(
      source.linkedin
    ),
    authorization: safeString(
      source.authorization
    ),
    summary: safeString(source.summary),

    skills: normalizeSkills(
      source.skills
    ),

    experience:
      normalizeExperience(
        source.experience
      ),

    projects:
      normalizeProjects(
        source.projects
      ),

    education:
      normalizeEducation(
        source.education
      ),
  };
}


/* =========================================================
   RESUME PREVIEW
   ========================================================= */

function ResumeSection({
  title,
  children,
}) {
  return (
    <section className="resume-preview-section">
      <div className="resume-preview-section-title">
        {title}
      </div>

      {children}
    </section>
  );
}


function ResumePreview({
  resume,
}) {
  if (!resume) {
    return null;
  }

  return (
    <div className="resume-preview-paper">

      {/* HEADER */}

      <div className="resume-preview-header">

        {resume.name && (
          <div className="resume-preview-name">
            {resume.name}
          </div>
        )}

        {resume.location && (
          <div className="resume-preview-location">
            {resume.location}
          </div>
        )}

        {(resume.email ||
          resume.phone ||
          resume.linkedin) && (
          <div className="resume-preview-contact">
            {[
              resume.email,
              resume.phone,
              resume.linkedin,
            ]
              .filter(Boolean)
              .join(" | ")}
          </div>
        )}

        {resume.authorization && (
          <div className="resume-preview-authorization">
            {resume.authorization}
          </div>
        )}

      </div>


      {/* SUMMARY */}

      {resume.summary && (
        <ResumeSection
          title="Professional Summary"
        >
          <p className="resume-preview-summary">
            {resume.summary}
          </p>
        </ResumeSection>
      )}


      {/* SKILLS */}

      {Object.values(
        resume.skills || {}
      ).some(
        (items) =>
          Array.isArray(items) &&
          items.length > 0
      ) && (
        <ResumeSection
          title="Technical Skills"
        >
          <div className="resume-preview-skills">

            {Object.entries(
              resume.skills || {}
            ).map(
              ([category, values]) => {
                if (
                  !values ||
                  !values.length
                ) {
                  return null;
                }

                return (
                  <div
                    key={category}
                    className="resume-preview-skill"
                  >
                    <strong>
                      {category}:
                    </strong>

                    <span>
                      {values.join(", ")}
                    </span>
                  </div>
                );
              }
            )}

          </div>
        </ResumeSection>
      )}


      {/* EXPERIENCE */}

      {resume.experience.length > 0 && (
        <ResumeSection
          title="Professional Experience"
        >
          {resume.experience.map(
            (job, index) => (
              <div
                key={`${job.company}-${index}`}
                className="resume-preview-job"
              >

                <div className="resume-preview-job-line">

                  <strong>
                    {job.title}
                  </strong>

                  {job.dates && (
                    <span>
                      {job.dates}
                    </span>
                  )}

                </div>


                {(job.company ||
                  job.location) && (
                  <div className="resume-preview-company">
                    {[
                      job.company,
                      job.location,
                    ]
                      .filter(Boolean)
                      .join(" | ")}
                  </div>
                )}


                {job.bullets.length > 0 && (
                  <ul>
                    {job.bullets.map(
                      (bullet, bulletIndex) => (
                        <li
                          key={bulletIndex}
                        >
                          {bullet}
                        </li>
                      )
                    )}
                  </ul>
                )}

              </div>
            )
          )}
        </ResumeSection>
      )}


      {/* PROJECTS */}

      {resume.projects.length > 0 && (
        <ResumeSection
          title="Projects"
        >
          {resume.projects.map(
            (project, index) => (
              <div
                key={`${project.title}-${index}`}
                className="resume-preview-project"
              >

                <div className="resume-preview-project-title">
                  {project.title}
                </div>


                {project.technologies.length >
                  0 && (
                  <div className="resume-preview-technologies">
                    {project.technologies.join(
                      ", "
                    )}
                  </div>
                )}


                {project.bullets.length >
                  0 && (
                  <ul>
                    {project.bullets.map(
                      (
                        bullet,
                        bulletIndex
                      ) => (
                        <li
                          key={
                            bulletIndex
                          }
                        >
                          {bullet}
                        </li>
                      )
                    )}
                  </ul>
                )}

              </div>
            )
          )}
        </ResumeSection>
      )}


      {/* EDUCATION */}

      {resume.education.length > 0 && (
        <ResumeSection
          title="Education"
        >
          {resume.education.map(
            (item, index) => (
              <div
                key={`${item.institution}-${index}`}
                className="resume-preview-education"
              >

                <div className="resume-preview-education-line">

                  <strong>
                    {item.degree}
                  </strong>

                  {item.dates && (
                    <span>
                      {item.dates}
                    </span>
                  )}

                </div>


                {(item.institution ||
                  item.location) && (
                  <div className="resume-preview-company">
                    {[
                      item.institution,
                      item.location,
                    ]
                      .filter(Boolean)
                      .join(" | ")}
                  </div>
                )}

              </div>
            )
          )}
        </ResumeSection>
      )}

    </div>
  );
}


/* =========================================================
   COVER LETTER PREVIEW
   ========================================================= */

function CoverLetterPreview({
  content,
}) {
  if (!content) {
    return null;
  }

  const paragraphs = content
    .split(/\n\s*\n/)
    .map((item) => item.trim())
    .filter(Boolean);

  return (
    <div className="cover-letter-paper">
      {paragraphs.map(
        (paragraph, index) => (
          <p key={index}>
            {paragraph}
          </p>
        )
      )}
    </div>
  );
}


/* =========================================================
   MAIN APP
   ========================================================= */

export default function App() {

  /* -------------------------------------------------------
     STATE
     ------------------------------------------------------- */

  const [resumeFile, setResumeFile] =
    useState(null);

  const [jobUrl, setJobUrl] =
    useState("");

  const [jobDescription, setJobDescription] =
    useState("");

  // This stores the description returned by
  // the backend after Ashby URL extraction.
  const [
    resolvedJobDescription,
    setResolvedJobDescription,
  ] = useState("");

  const [resumeText, setResumeText] =
    useState("");

  const [analysis, setAnalysis] =
    useState(null);

  const [
    tailoredResume,
    setTailoredResume,
  ] = useState(null);

  const [coverLetter, setCoverLetter] =
    useState("");

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [loadingAction, setLoadingAction] =
    useState("");


  /* -------------------------------------------------------
     ACTIVE JOB DESCRIPTION
     ------------------------------------------------------- */

  const activeJobDescription =
    useMemo(() => {
      return (
        resolvedJobDescription.trim() ||
        jobDescription.trim()
      );
    }, [
      resolvedJobDescription,
      jobDescription,
    ]);


  /* -------------------------------------------------------
     CLEAR RESULTS
     ------------------------------------------------------- */

  const clearResults = () => {
    setAnalysis(null);
    setTailoredResume(null);
    setCoverLetter("");
    setResumeText("");
    setResolvedJobDescription("");
  };


  /* -------------------------------------------------------
     ANALYZE JOB
     ------------------------------------------------------- */

  const analyzeJob = async () => {
    setError("");
    setSuccess("");

    clearResults();

    if (!resumeFile) {
      setError(
        "Please upload your resume first."
      );
      return;
    }

    if (
      !jobDescription.trim() &&
      !jobUrl.trim()
    ) {
      setError(
        "Please provide a job description or a job URL."
      );
      return;
    }

    setLoadingAction("analyze");

    try {
      const formData =
        new FormData();

      formData.append(
        "resume",
        resumeFile
      );

      formData.append(
        "job_description",
        jobDescription.trim()
      );

      formData.append(
        "job_url",
        jobUrl.trim()
      );

      const response =
        await fetch(
          `${API_URL}/analyze`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await parseErrorResponse(
          response
        );


      const extractedDescription =
        safeString(
          data.job_description
        );

      const returnedResumeText =
        safeString(
          data.resume_text
        );

      const returnedAnalysis =
        data.analysis || null;


      /* ---------------------------------------------------
         IMPORTANT:
         Save the extracted job description.
         This is what makes Tailor + Cover Letter work
         after using only an Ashby URL.
         --------------------------------------------------- */

      setResolvedJobDescription(
        extractedDescription
      );

      setJobDescription(
        extractedDescription ||
        jobDescription.trim()
      );

      setResumeText(
        returnedResumeText
      );

      setAnalysis(
        returnedAnalysis
      );


      setSuccess(
        extractedDescription
          ? "Job analyzed successfully. The job description was extracted and is ready for resume tailoring and cover letter generation."
          : "Job analyzed successfully."
      );

    } catch (err) {

      setError(
        err.message ||
        "Could not analyze the job."
      );

    } finally {

      setLoadingAction("");
    }
  };


  /* -------------------------------------------------------
     TAILOR RESUME
     ------------------------------------------------------- */

  const tailorResume = async () => {
    setError("");
    setSuccess("");

    if (!resumeText.trim()) {
      setError(
        "Resume content is missing. Please analyze the job first."
      );
      return;
    }

    if (!activeJobDescription) {
      setError(
        "Job description is missing. Please analyze the job first."
      );
      return;
    }

    setLoadingAction("tailor");

    try {

      const response =
        await fetch(
          `${API_URL}/tailor`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              resume_text:
                resumeText,

              job_description:
                activeJobDescription,

              analysis:
                analysis || null,
            }),
          }
        );


      const data =
        await parseErrorResponse(
          response
        );


      if (
        !data.tailored_resume
      ) {
        throw new Error(
          "The backend did not return a tailored resume."
        );
      }


      const normalized =
        normalizeResume(
          data.tailored_resume
        );


      setTailoredResume(
        normalized
      );


      setSuccess(
        "Tailored resume generated successfully."
      );

    } catch (err) {

      setError(
        err.message ||
        "Could not tailor the resume."
      );

    } finally {

      setLoadingAction("");
    }
  };


  /* -------------------------------------------------------
     GENERATE COVER LETTER
     ------------------------------------------------------- */

  const generateCoverLetter =
    async () => {

      setError("");
      setSuccess("");

      if (!resumeText.trim()) {
        setError(
          "Resume content is missing. Please analyze the job first."
        );
        return;
      }

      if (!activeJobDescription) {
        setError(
          "Job description is missing. Please analyze the job first."
        );
        return;
      }

      setLoadingAction(
        "cover-letter"
      );

      try {

        const response =
          await fetch(
            `${API_URL}/cover-letter`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                resume_text:
                  resumeText,

                job_description:
                  activeJobDescription,

                analysis:
                  analysis || null,
              }),
            }
          );


        const data =
          await parseErrorResponse(
            response
          );


        const generated =
          safeString(
            data.cover_letter
          );


        if (!generated) {
          throw new Error(
            "The backend did not return a cover letter."
          );
        }


        setCoverLetter(
          generated
        );


        setSuccess(
          "Cover letter generated successfully."
        );

      } catch (err) {

        setError(
          err.message ||
          "Could not generate the cover letter."
        );

      } finally {

        setLoadingAction("");
      }
    };


  /* -------------------------------------------------------
     DOWNLOAD RESUME
     ------------------------------------------------------- */

  const downloadResume =
    async () => {

      setError("");
      setSuccess("");

      if (!tailoredResume) {
        setError(
          "Please generate the tailored resume first."
        );
        return;
      }

      setLoadingAction(
        "download-resume"
      );

      try {

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
                  tailoredResume,
              }),
            }
          );


        if (!response.ok) {

          const data =
            await parseErrorResponse(
              response
            );

          throw new Error(
            data.detail ||
            "Could not download the resume."
          );
        }


        const blob =
          await response.blob();


        const url =
          window.URL.createObjectURL(
            blob
          );


        const link =
          document.createElement(
            "a"
          );

        link.href = url;

        link.download =
          "tailored_resume.docx";

        document.body.appendChild(
          link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
          url
        );


        setSuccess(
          "Tailored resume downloaded."
        );

      } catch (err) {

        setError(
          err.message ||
          "Could not download the resume."
        );

      } finally {

        setLoadingAction("");
      }
    };


  /* -------------------------------------------------------
     DOWNLOAD COVER LETTER
     ------------------------------------------------------- */

  const downloadCoverLetter =
    async () => {

      setError("");
      setSuccess("");

      if (!coverLetter.trim()) {
        setError(
          "Please generate the cover letter first."
        );
        return;
      }

      setLoadingAction(
        "download-cover-letter"
      );

      try {

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

          const data =
            await parseErrorResponse(
              response
            );

          throw new Error(
            data.detail ||
            "Could not download the cover letter."
          );
        }


        const blob =
          await response.blob();


        const url =
          window.URL.createObjectURL(
            blob
          );


        const link =
          document.createElement(
            "a"
          );

        link.href = url;

        link.download =
          "cover_letter.docx";

        document.body.appendChild(
          link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
          url
        );


        setSuccess(
          "Cover letter downloaded."
        );

      } catch (err) {

        setError(
          err.message ||
          "Could not download the cover letter."
        );

      } finally {

        setLoadingAction("");
      }
    };


  /* =======================================================
     UI
     ======================================================= */

  return (
    <div className="app">

      {/* ---------------------------------------------------
          HEADER
          --------------------------------------------------- */}

      <header className="hero">

        <div className="hero-badge">
          AI-powered job applications
        </div>

        <h1>
          AI Job Application Agent
        </h1>

        <p>
          Turn a job posting into a
          stronger application.
        </p>

        <div className="hero-description">
          Upload your resume, provide
          a job posting, and let AI
          analyze the opportunity,
          identify gaps, tailor your
          resume, and prepare your
          cover letter.
        </div>

      </header>


      {/* ---------------------------------------------------
          MAIN CARD
          --------------------------------------------------- */}

      <main className="main-container">

        {/* -------------------------------------------------
            INPUTS
            ------------------------------------------------- */}

        <section className="card">

          <h2>
            Application Preparation
          </h2>


          {/* RESUME */}

          <div className="form-group">

            <label>
              Your Resume
            </label>

            <div className="upload-box">

              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(event) => {
                  const file =
                    event.target.files?.[0] ||
                    null;

                  setResumeFile(file);

                  if (file) {
                    setSuccess(
                      `Resume selected: ${file.name}`
                    );
                  }
                }}
              />

              {resumeFile && (
                <div className="file-selected">
                  {resumeFile.name}
                </div>
              )}

            </div>

            <small>
              PDF or DOCX
            </small>

          </div>


          {/* JOB URL */}

          <div className="form-group">

            <label>
              Job posting URL
            </label>

            <input
              type="url"
              value={jobUrl}
              onChange={(event) =>
                setJobUrl(
                  event.target.value
                )
              }
              placeholder="https://jobs.ashbyhq.com/..."
            />

          </div>


          {/* JOB DESCRIPTION */}

          <div className="form-group">

            <label>
              Job description
            </label>

            <textarea
              value={jobDescription}
              onChange={(event) => {
                setJobDescription(
                  event.target.value
                );

                setResolvedJobDescription(
                  ""
                );
              }}
              placeholder="Paste the job description here..."
              rows={12}
            />

            <small>
              You can paste the job description
              or use a supported Ashby job URL.
            </small>

          </div>


          {/* ERROR */}

          {error && (
            <div className="alert alert-error">
              <span>⚠</span>
              <span>{error}</span>
            </div>
          )}


          {/* SUCCESS */}

          {success && (
            <div className="alert alert-success">
              <span>✓</span>
              <span>{success}</span>
            </div>
          )}


          {/* ANALYZE BUTTON */}

          <button
            className="primary-button"
            onClick={analyzeJob}
            disabled={
              loadingAction !== ""
            }
          >
            {loadingAction ===
            "analyze"
              ? "Analyzing Job..."
              : "Analyze Job →"}
          </button>

        </section>


        {/* -------------------------------------------------
            ANALYSIS
            ------------------------------------------------- */}

        {analysis && (
          <section className="card">

            <div className="section-header">

              <div>
                <div className="eyebrow">
                  AI Analysis Complete
                </div>

                <h2>
                  Application Analysis
                </h2>
              </div>

            </div>


            {/* OVERVIEW */}

            <div className="overview-grid">

              <div className="metric-card">

                <span>
                  Match Score
                </span>

                <strong>
                  {analysis.match_score ??
                    0}
                  /100
                </strong>

              </div>


              <div className="metric-card">

                <span>
                  Job Title
                </span>

                <strong>
                  {analysis.job_title ||
                    "Job"}
                </strong>

              </div>


              <div className="metric-card">

                <span>
                  Assessment
                </span>

                <strong>
                  {analysis.match_level ||
                    "Analysis complete"}
                </strong>

              </div>

            </div>


            {/* SUMMARY */}

            {analysis.summary && (
              <div className="result-block">

                <h3>
                  Assessment
                </h3>

                <p>
                  {analysis.summary}
                </p>

              </div>
            )}


            {/* MATCHING SKILLS */}

            {safeArray(
              analysis.matching_skills
            ).length > 0 && (
              <div className="result-block">

                <h3>
                  Matching Skills
                </h3>

                <div className="tag-list">

                  {safeArray(
                    analysis.matching_skills
                  ).map(
                    (
                      skill,
                      index
                    ) => (
                      <div
                        className="tag-item"
                        key={index}
                      >
                        ✓{" "}
                        {safeString(
                          skill
                        )}
                      </div>
                    )
                  )}

                </div>

              </div>
            )}


            {/* SKILL GAPS */}

            {safeArray(
              analysis.skill_gaps
            ).length > 0 && (
              <div className="result-block">

                <h3>
                  Skill Gaps
                </h3>

                <div className="gap-list">

                  {safeArray(
                    analysis.skill_gaps
                  ).map(
                    (
                      gap,
                      index
                    ) => (
                      <div
                        className="gap-item"
                        key={index}
                      >
                        <span>
                          !
                        </span>

                        <span>
                          {safeString(
                            gap
                          )}
                        </span>
                      </div>
                    )
                  )}

                </div>

              </div>
            )}


            {/* EXPERIENCE */}

            {analysis.experience && (
              <div className="result-block">

                <h3>
                  Experience Match
                </h3>

                <div className="comparison-grid">

                  <div>
                    <h4>
                      Required
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .experience
                          ?.required
                      ) ||
                        "Not specified"}
                    </p>
                  </div>


                  <div>
                    <h4>
                      Candidate
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .experience
                          ?.candidate
                      ) ||
                        "Not specified"}
                    </p>
                  </div>


                  <div>
                    <h4>
                      Assessment
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .experience
                          ?.assessment
                      ) ||
                        "Not specified"}
                    </p>
                  </div>

                </div>

              </div>
            )}


            {/* EDUCATION */}

            {analysis.education && (
              <div className="result-block">

                <h3>
                  Education Match
                </h3>

                <div className="comparison-grid">

                  <div>
                    <h4>
                      Required
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .education
                          ?.required
                      ) ||
                        "Not specified"}
                    </p>
                  </div>


                  <div>
                    <h4>
                      Candidate
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .education
                          ?.candidate
                      ) ||
                        "Not specified"}
                    </p>
                  </div>


                  <div>
                    <h4>
                      Assessment
                    </h4>

                    <p>
                      {safeString(
                        analysis
                          .education
                          ?.assessment
                      ) ||
                        "Not specified"}
                    </p>
                  </div>

                </div>

              </div>
            )}


            {/* KEYWORDS */}

            {safeArray(
              analysis.keywords
            ).length > 0 && (
              <div className="result-block">

                <h3>
                  Important Keywords
                </h3>

                <div className="keyword-list">

                  {safeArray(
                    analysis.keywords
                  ).map(
                    (
                      keyword,
                      index
                    ) => (
                      <span
                        className="keyword"
                        key={index}
                      >
                        {safeString(
                          keyword
                        )}
                      </span>
                    )
                  )}

                </div>

              </div>
            )}


            {/* ------------------------------------------------
                APPLICATION PREPARATION
                ------------------------------------------------ */}

            <div className="application-actions">

              <h3>
                Prepare Your Application
              </h3>

              <p>
                Use the extracted job
                description to create your
                tailored resume and
                personalized cover letter.
              </p>


              <div className="button-row">

                <button
                  className="secondary-button"
                  onClick={
                    tailorResume
                  }
                  disabled={
                    loadingAction !== ""
                  }
                >
                  {loadingAction ===
                  "tailor"
                    ? "Tailoring Resume..."
                    : "Tailor My Resume"}
                </button>


                <button
                  className="secondary-button"
                  onClick={
                    generateCoverLetter
                  }
                  disabled={
                    loadingAction !== ""
                  }
                >
                  {loadingAction ===
                  "cover-letter"
                    ? "Generating..."
                    : "Generate Cover Letter"}
                </button>

              </div>

            </div>

          </section>
        )}


        {/* -------------------------------------------------
            TAILORED RESUME
            ------------------------------------------------- */}

        {tailoredResume && (
          <section className="card">

            <div className="section-header">

              <div>
                <div className="eyebrow">
                  Resume Tailoring Complete
                </div>

                <h2>
                  Tailored Resume
                </h2>
              </div>


              <button
                className="download-button"
                onClick={
                  downloadResume
                }
                disabled={
                  loadingAction !== ""
                }
              >
                {loadingAction ===
                "download-resume"
                  ? "Preparing..."
                  : "Download Resume"}
              </button>

            </div>


            <p className="muted">
              Tailored for this specific
              job while keeping the
              candidate's experience
              truthful.
            </p>


            <ResumePreview
              resume={
                tailoredResume
              }
            />

          </section>
        )}


        {/* -------------------------------------------------
            COVER LETTER
            ------------------------------------------------- */}

        {coverLetter && (
          <section className="card">

            <div className="section-header">

              <div>
                <div className="eyebrow">
                  Personalized for this job
                </div>

                <h2>
                  Cover Letter
                </h2>
              </div>


              <button
                className="download-button"
                onClick={
                  downloadCoverLetter
                }
                disabled={
                  loadingAction !== ""
                }
              >
                {loadingAction ===
                "download-cover-letter"
                  ? "Preparing..."
                  : "Download Cover Letter"}
              </button>

            </div>


            <CoverLetterPreview
              content={
                coverLetter
              }
            />

          </section>
        )}

      </main>


      {/* ---------------------------------------------------
          FOOTER
          --------------------------------------------------- */}

      <footer className="footer">
        AI Job Application Agent
      </footer>

    </div>
  );
}