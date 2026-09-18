import { useState } from "react";

import {
  Upload,
  Link,
  Briefcase,
  Sparkles,
  FileText,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Target,
  Download,
  Mail,
} from "lucide-react";


function App() {

  // =======================================================
  // STATE
  // =======================================================

  const [resume, setResume] =
    useState(null);

  const [jobUrl, setJobUrl] =
    useState("");

  const [jobDescription, setJobDescription] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [tailoring, setTailoring] =
    useState(false);

  const [generatingLetter, setGeneratingLetter] =
    useState(false);

  const [downloadingResume, setDownloadingResume] =
    useState(false);

  const [downloadingLetter, setDownloadingLetter] =
    useState(false);

  const [analysis, setAnalysis] =
    useState(null);

  const [tailoredResume, setTailoredResume] =
    useState("");

  const [coverLetter, setCoverLetter] =
    useState("");

  const [error, setError] =
    useState("");


  // =======================================================
  // RESUME UPLOAD
  // =======================================================

  const handleResumeChange = (event) => {

    const file =
      event.target.files[0];

    if (!file) {
      return;
    }

    const fileName =
      file.name.toLowerCase();

    const validFile =
      fileName.endsWith(".pdf") ||
      fileName.endsWith(".docx");

    if (!validFile) {

      setError(
        "Please upload a PDF or DOCX resume."
      );

      setResume(null);

      return;
    }

    setError("");

    setResume(file);

    setAnalysis(null);
    setTailoredResume("");
    setCoverLetter("");
  };


  // =======================================================
  // ANALYZE
  // =======================================================

  const handleAnalyze = async () => {

    setError("");

    setAnalysis(null);
    setTailoredResume("");
    setCoverLetter("");

    if (!resume) {

      setError(
        "Please upload your resume first."
      );

      return;
    }

    if (!jobDescription.trim()) {

      setError(
        "Please paste the complete job description."
      );

      return;
    }

    try {

      setLoading(true);

      const formData =
        new FormData();

      formData.append(
        "resume",
        resume
      );

      formData.append(
        "job_description",
        jobDescription
      );

      const response =
        await fetch(
          "http://127.0.0.1:8000/analyze",
          {
            method: "POST",
            body: formData,
          }
        );

      if (!response.ok) {

        throw new Error(
          `Backend returned HTTP ${response.status}`
        );
      }

      const data =
        await response.json();

      if (!data.success) {

        throw new Error(
          data.error ||
          "AI analysis failed."
        );
      }

      setAnalysis(
        data.analysis
      );

      setTimeout(() => {

        document
          .getElementById(
            "analysis-results"
          )
          ?.scrollIntoView({
            behavior: "smooth",
          });

      }, 100);

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Could not connect to the Python AI backend."
      );

    } finally {

      setLoading(false);
    }
  };


  // =======================================================
  // TAILOR RESUME
  // =======================================================

  const handleTailorResume =
    async () => {

      setError("");

      if (!resume) {

        setError(
          "Please upload your resume first."
        );

        return;
      }

      if (!jobDescription.trim()) {

        setError(
          "Please provide the job description."
        );

        return;
      }

      if (!analysis) {

        setError(
          "Analyze the job before tailoring your resume."
        );

        return;
      }

      try {

        setTailoring(true);

        const formData =
          new FormData();

        formData.append(
          "resume",
          resume
        );

        formData.append(
          "job_description",
          jobDescription
        );

        formData.append(
          "analysis",
          JSON.stringify(analysis)
        );

        const response =
          await fetch(
            "http://127.0.0.1:8000/tailor",
            {
              method: "POST",
              body: formData,
            }
          );

        if (!response.ok) {

          throw new Error(
            `Backend returned HTTP ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!data.success) {

          throw new Error(
            data.error ||
            "Resume tailoring failed."
          );
        }

        setTailoredResume(
          data.tailored_resume
        );

        setTimeout(() => {

          document
            .getElementById(
              "tailored-resume"
            )
            ?.scrollIntoView({
              behavior: "smooth",
            });

        }, 100);

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Could not tailor the resume."
        );

      } finally {

        setTailoring(false);
      }
    };


  // =======================================================
  // GENERATE COVER LETTER
  // =======================================================

  const handleGenerateCoverLetter =
    async () => {

      setError("");

      if (!resume) {

        setError(
          "Please upload your resume first."
        );

        return;
      }

      if (!jobDescription.trim()) {

        setError(
          "Please provide the job description."
        );

        return;
      }

      if (!analysis) {

        setError(
          "Analyze the job first."
        );

        return;
      }

      if (!tailoredResume) {

        setError(
          "Tailor the resume before generating the cover letter."
        );

        return;
      }

      try {

        setGeneratingLetter(true);

        const formData =
          new FormData();

        formData.append(
          "resume",
          resume
        );

        formData.append(
          "job_description",
          jobDescription
        );

        formData.append(
          "analysis",
          JSON.stringify(analysis)
        );

        formData.append(
          "tailored_resume",
          tailoredResume
        );

        const response =
          await fetch(
            "http://127.0.0.1:8000/cover-letter",
            {
              method: "POST",
              body: formData,
            }
          );

        if (!response.ok) {

          throw new Error(
            `Backend returned HTTP ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!data.success) {

          throw new Error(
            data.error ||
            "Cover letter generation failed."
          );
        }

        setCoverLetter(
          data.cover_letter
        );

        setTimeout(() => {

          document
            .getElementById(
              "cover-letter"
            )
            ?.scrollIntoView({
              behavior: "smooth",
            });

        }, 100);

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Could not generate the cover letter."
        );

      } finally {

        setGeneratingLetter(false);
      }
    };


  // =======================================================
  // DOWNLOAD RESUME
  // =======================================================

  const handleDownloadResume =
    async () => {

      if (!tailoredResume) {
        return;
      }

      try {

        setDownloadingResume(true);

        const formData =
          new FormData();

        formData.append(
          "tailored_resume",
          tailoredResume
        );

        const response =
          await fetch(
            "http://127.0.0.1:8000/download-resume",
            {
              method: "POST",
              body: formData,
            }
          );

        if (!response.ok) {

          throw new Error(
            "Could not create the resume document."
          );
        }

        const blob =
          await response.blob();

        const url =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement("a");

        link.href = url;

        link.download =
          "Tailored_Resume.docx";

        document.body.appendChild(link);

        link.click();

        link.remove();

        window.URL.revokeObjectURL(url);

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Could not download the resume."
        );

      } finally {

        setDownloadingResume(false);
      }
    };


  // =======================================================
  // DOWNLOAD COVER LETTER
  // =======================================================

  const handleDownloadCoverLetter =
    async () => {

      if (!coverLetter) {
        return;
      }

      try {

        setDownloadingLetter(true);

        const formData =
          new FormData();

        formData.append(
          "cover_letter",
          coverLetter
        );

        const response =
          await fetch(
            "http://127.0.0.1:8000/download-cover-letter",
            {
              method: "POST",
              body: formData,
            }
          );

        if (!response.ok) {

          throw new Error(
            "Could not create the cover letter document."
          );
        }

        const blob =
          await response.blob();

        const url =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement("a");

        link.href = url;

        link.download =
          "Cover_Letter.docx";

        document.body.appendChild(link);

        link.click();

        link.remove();

        window.URL.revokeObjectURL(url);

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Could not download the cover letter."
        );

      } finally {

        setDownloadingLetter(false);
      }
    };


  // =======================================================
  // SCORE LABEL
  // =======================================================

  const getScoreLabel =
    (score) => {

      if (score >= 80) {
        return "Strong Match";
      }

      if (score >= 60) {
        return "Moderate Match";
      }

      return "Needs Improvement";
    };


  // =======================================================
  // UI
  // =======================================================

  return (

    <div className="min-h-screen bg-slate-950 text-white">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="border-b border-slate-800">

        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">

          <div className="flex items-center gap-3">

            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600">

              <Sparkles size={21} />

            </div>

            <div>

              <h1 className="text-lg font-semibold">
                AI Job Application Agent
              </h1>

              <p className="text-xs text-slate-500">
                Intelligent application assistant
              </p>

            </div>

          </div>


          <nav className="hidden gap-8 text-sm md:flex">

            <span className="text-white">
              Dashboard
            </span>

            <span className="text-slate-500">
              Applications
            </span>

            <span className="text-slate-500">
              My Resume
            </span>

            <span className="text-slate-500">
              Settings
            </span>

          </nav>

        </div>

      </header>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="mx-auto max-w-7xl px-6 py-12">


        {/* HERO */}

        <section className="mb-10 max-w-4xl">

          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-sm text-violet-300">

            <Sparkles size={15} />

            AI-powered job applications

          </div>


          <h2 className="text-4xl font-bold tracking-tight md:text-5xl">

            Turn a job posting into a

            <span className="text-violet-400">
              {" "}stronger application.
            </span>

          </h2>


          <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-400">

            Upload your resume, provide a job posting,
            and let the AI analyze the opportunity,
            identify gaps, tailor your resume,
            and prepare your cover letter.

          </p>

        </section>


        {/* =================================================
            ERROR
        ================================================= */}

        {error && (

          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300">

            <AlertCircle
              size={20}
              className="mt-0.5 shrink-0"
            />

            <div>

              <p className="font-semibold">
                Something went wrong
              </p>

              <p className="mt-1 text-sm">
                {error}
              </p>

            </div>

          </div>

        )}


        {/* =================================================
            INPUTS
        ================================================= */}

        <div className="grid gap-6 lg:grid-cols-3">


          {/* RESUME */}

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

            <div className="mb-5 flex items-center gap-3">

              <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">

                <Upload size={20} />

              </div>

              <div>

                <h3 className="font-semibold">
                  Your Resume
                </h3>

                <p className="text-sm text-slate-500">
                  PDF or Word document
                </p>

              </div>

            </div>


            <label className="flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/50 px-5 text-center transition hover:border-violet-500">

              <Upload
                className="mb-3 text-slate-500"
                size={28}
              />


              {resume ? (

                <>

                  <p className="max-w-full truncate font-medium">
                    {resume.name}
                  </p>

                  <p className="mt-1 text-sm text-emerald-400">
                    Resume uploaded
                  </p>

                </>

              ) : (

                <>

                  <p className="font-medium">
                    Drop your resume here
                  </p>

                  <p className="mt-2 text-sm text-slate-500">
                    or click to browse
                  </p>

                </>

              )}


              <input
                type="file"
                accept=".pdf,.docx"
                onChange={handleResumeChange}
                className="hidden"
              />

            </label>


            {resume && (

              <div className="mt-4 flex items-center gap-2 text-sm text-emerald-400">

                <CheckCircle2 size={16} />

                Ready for analysis

              </div>

            )}

          </div>


          {/* JOB */}

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

            <div className="mb-5 flex items-center gap-3">

              <div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-400">

                <Briefcase size={20} />

              </div>

              <div>

                <h3 className="font-semibold">
                  Job Posting
                </h3>

                <p className="text-sm text-slate-500">
                  URL or job description
                </p>

              </div>

            </div>


            <div className="relative">

              <Link
                size={17}
                className="absolute left-4 top-3.5 text-slate-600"
              />

              <input
                type="url"
                value={jobUrl}
                onChange={(event) =>
                  setJobUrl(event.target.value)
                }
                placeholder="https://company.com/jobs/..."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm outline-none focus:border-violet-500"
              />

            </div>


            <div className="my-4 flex items-center gap-3 text-sm text-slate-600">

              <div className="h-px flex-1 bg-slate-800" />

              OR

              <div className="h-px flex-1 bg-slate-800" />

            </div>


            <textarea
              value={jobDescription}
              onChange={(event) =>
                setJobDescription(
                  event.target.value
                )
              }
              placeholder="Paste the complete job description..."
              rows={8}
              className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-violet-500"
            />

          </div>


          {/* AI AGENT */}

          <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-b from-violet-500/10 to-slate-900 p-6">

            <div className="mb-5 flex items-center gap-3">

              <div className="rounded-xl bg-violet-500/15 p-3 text-violet-400">

                <Sparkles size={20} />

              </div>

              <div>

                <h3 className="font-semibold">
                  AI Agent
                </h3>

                <p className="text-sm text-slate-500">
                  Application preparation
                </p>

              </div>

            </div>


            <div className="space-y-3">

              <AgentStep
                icon={<FileText size={16} />}
                text="Analyze job requirements"
              />

              <AgentStep
                icon={<Briefcase size={16} />}
                text="Compare your experience"
              />

              <AgentStep
                icon={<Target size={16} />}
                text="Identify skill gaps"
              />

              <AgentStep
                icon={<Sparkles size={16} />}
                text="Prepare application"
              />

            </div>


            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3.5 font-semibold transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >

              {loading ? (

                <>

                  <Loader2
                    size={18}
                    className="animate-spin"
                  />

                  Analyzing...

                </>

              ) : (

                <>

                  Analyze Job

                  <ArrowRight size={18} />

                </>

              )}

            </button>

          </div>

        </div>


        {/* =================================================
            ANALYSIS
        ================================================= */}

        {analysis && (

          <section
            id="analysis-results"
            className="mt-14"
          >

            <div className="mb-6">

              <div className="mb-2 flex items-center gap-2 text-violet-400">

                <Sparkles size={18} />

                <span className="text-sm font-semibold">
                  AI Analysis Complete
                </span>

              </div>

              <h2 className="text-2xl font-bold">
                Application Analysis
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Here's how your profile compares with this role.
              </p>

            </div>


            {/* SCORE */}

            <div className="grid gap-6 md:grid-cols-3">

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-sm text-slate-500">
                  Match Score
                </p>

                <div className="mt-3 flex items-end gap-2">

                  <span className="text-5xl font-bold text-violet-400">
                    {analysis.match_score ?? 0}
                  </span>

                  <span className="mb-2 text-slate-500">
                    /100
                  </span>

                </div>

                <p className="mt-3 text-sm font-medium text-violet-300">
                  {getScoreLabel(
                    analysis.match_score ?? 0
                  )}
                </p>

              </div>


              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-sm text-slate-500">
                  Job Title
                </p>

                <h3 className="mt-3 text-xl font-semibold">
                  {analysis.job_title ||
                    "Job title not identified"}
                </h3>

              </div>


              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-sm text-slate-500">
                  Assessment
                </p>

                <p className="mt-3 text-sm leading-6 text-slate-300">
                  {analysis.match_summary ||
                    "No summary returned."}
                </p>

              </div>

            </div>


            {/* SKILLS */}

            <div className="mt-6 grid gap-6 md:grid-cols-2">


              <SkillCard
                title="Matching Skills"
                description="Skills supported by your resume"
                items={analysis.matching_skills}
                icon={
                  <CheckCircle2 size={18} />
                }
                iconClass="text-emerald-400"
              />


              <SkillCard
                title="Skill Gaps"
                description="Requirements needing attention"
                items={analysis.skill_gaps}
                icon={
                  <AlertCircle size={18} />
                }
                iconClass="text-orange-400"
              />

            </div>


            {/* EXPERIENCE */}

            {analysis.experience && (

              <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">

                <h3 className="font-semibold">
                  Experience Match
                </h3>

                <p className="mt-1 text-sm text-slate-500">
                  Comparison between the role and your background
                </p>


                <div className="mt-5 grid gap-4 md:grid-cols-3">

                  <InfoCard
                    title="Required"
                    value={
                      analysis.experience.required
                    }
                  />

                  <InfoCard
                    title="Candidate"
                    value={
                      analysis.experience.candidate
                    }
                  />

                  <InfoCard
                    title="Assessment"
                    value={
                      analysis.experience.assessment
                    }
                  />

                </div>

              </div>

            )}


            {/* KEYWORDS */}

            {analysis.keywords?.length > 0 && (

              <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">

                <h3 className="mb-4 font-semibold">
                  Important Keywords
                </h3>

                <div className="flex flex-wrap gap-2">

                  {analysis.keywords.map(
                    (keyword, index) => (

                      <span
                        key={index}
                        className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-300"
                      >
                        {keyword}
                      </span>

                    )
                  )}

                </div>

              </div>

            )}


            {/* =================================================
                ACTIONS
            ================================================= */}

            <div className="mt-6 rounded-2xl border border-violet-500/20 bg-violet-500/5 p-6">

              <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">

                <div>

                  <h3 className="font-semibold">
                    Prepare your application
                  </h3>

                  <p className="mt-1 text-sm text-slate-500">
                    Tailor your resume and generate a personalized cover letter.
                  </p>

                </div>


                <button
                  onClick={handleTailorResume}
                  disabled={tailoring}
                  className="flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
                >

                  {tailoring ? (

                    <>

                      <Loader2
                        size={17}
                        className="animate-spin"
                      />

                      Tailoring...

                    </>

                  ) : (

                    <>

                      Tailor My Resume

                      <ArrowRight size={17} />

                    </>

                  )}

                </button>

              </div>

            </div>

          </section>

        )}


        {/* =================================================
            TAILORED RESUME
        ================================================= */}

        {tailoredResume && (

          <section
            id="tailored-resume"
            className="mt-10 rounded-2xl border border-violet-500/20 bg-slate-900 p-6"
          >

            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

              <div className="flex items-center gap-3">

                <div className="rounded-xl bg-violet-500/10 p-3 text-violet-400">

                  <FileText size={20} />

                </div>

                <div>

                  <h2 className="text-2xl font-bold">
                    Tailored Resume
                  </h2>

                  <p className="text-sm text-slate-500">
                    Tailored for this specific job
                  </p>

                </div>

              </div>


              <button
                onClick={handleDownloadResume}
                disabled={downloadingResume}
                className="flex items-center justify-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-5 py-3 text-sm font-semibold text-violet-300 transition hover:bg-violet-500/20 disabled:opacity-60"
              >

                {downloadingResume ? (

                  <>

                    <Loader2
                      size={17}
                      className="animate-spin"
                    />

                    Creating DOCX...

                  </>

                ) : (

                  <>

                    <Download size={17} />

                    Download Resume

                  </>

                )}

              </button>

            </div>


            <div className="mt-6 max-h-[700px] overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-6">

              <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-300">

                {tailoredResume}

              </pre>

            </div>


            <div className="mt-5 flex items-center gap-2 text-sm text-emerald-400">

              <CheckCircle2 size={17} />

              Resume tailoring complete

            </div>


            {/* COVER LETTER ACTION */}

            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5">

              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

                <div className="flex items-center gap-3">

                  <div className="rounded-lg bg-pink-500/10 p-2 text-pink-400">

                    <Mail size={18} />

                  </div>

                  <div>

                    <h3 className="font-semibold">
                      Generate Cover Letter
                    </h3>

                    <p className="text-sm text-slate-500">
                      Create a personalized letter for this role.
                    </p>

                  </div>

                </div>


                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={generatingLetter}
                  className="flex items-center justify-center gap-2 rounded-xl bg-pink-600 px-5 py-3 text-sm font-semibold transition hover:bg-pink-500 disabled:cursor-not-allowed disabled:opacity-60"
                >

                  {generatingLetter ? (

                    <>

                      <Loader2
                        size={17}
                        className="animate-spin"
                      />

                      Generating...

                    </>

                  ) : (

                    <>

                      <Mail size={17} />

                      Generate Cover Letter

                    </>

                  )}

                </button>

              </div>

            </div>

          </section>

        )}


        {/* =================================================
            COVER LETTER
        ================================================= */}

        {coverLetter && (

          <section
            id="cover-letter"
            className="mt-10 rounded-2xl border border-pink-500/20 bg-slate-900 p-6"
          >

            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

              <div className="flex items-center gap-3">

                <div className="rounded-xl bg-pink-500/10 p-3 text-pink-400">

                  <Mail size={20} />

                </div>

                <div>

                  <h2 className="text-2xl font-bold">
                    Cover Letter
                  </h2>

                  <p className="text-sm text-slate-500">
                    Personalized for this job
                  </p>

                </div>

              </div>


              <button
                onClick={handleDownloadCoverLetter}
                disabled={downloadingLetter}
                className="flex items-center justify-center gap-2 rounded-xl border border-pink-500/30 bg-pink-500/10 px-5 py-3 text-sm font-semibold text-pink-300 transition hover:bg-pink-500/20 disabled:opacity-60"
              >

                {downloadingLetter ? (

                  <>

                    <Loader2
                      size={17}
                      className="animate-spin"
                    />

                    Creating DOCX...

                  </>

                ) : (

                  <>

                    <Download size={17} />

                    Download Cover Letter

                  </>

                )}

              </button>

            </div>


            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6">

              <div className="whitespace-pre-wrap text-sm leading-7 text-slate-300">

                {coverLetter}

              </div>

            </div>


            <div className="mt-5 flex items-center gap-2 text-sm text-emerald-400">

              <CheckCircle2 size={17} />

              Cover letter generated successfully

            </div>

          </section>

        )}


      </main>

    </div>

  );
}


// =========================================================
// AGENT STEP
// =========================================================

function AgentStep({
  icon,
  text,
}) {

  return (

    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">

      <div className="text-violet-400">
        {icon}
      </div>

      <span className="text-sm text-slate-300">
        {text}
      </span>

    </div>

  );
}


// =========================================================
// SKILL CARD
// =========================================================

function SkillCard({
  title,
  description,
  items,
  icon,
  iconClass,
}) {

  return (

    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

      <div className="mb-5 flex items-center gap-3">

        <div className={`rounded-lg bg-slate-950 p-2 ${iconClass}`}>
          {icon}
        </div>

        <div>

          <h3 className="font-semibold">
            {title}
          </h3>

          <p className="text-sm text-slate-500">
            {description}
          </p>

        </div>

      </div>


      <div className="space-y-2">

        {items?.length > 0 ? (

          items.map(
            (item, index) => (

              <div
                key={index}
                className="flex items-center gap-3 rounded-lg bg-slate-950 px-4 py-3"
              >

                <span className={iconClass}>
                  {icon}
                </span>

                <span className="text-sm text-slate-300">

                  {typeof item === "object"
                    ? item.skill ||
                      item.name ||
                      item.description ||
                      JSON.stringify(item)
                    : item}

                </span>

              </div>

            )
          )

        ) : (

          <p className="text-sm text-slate-500">
            None returned.
          </p>

        )}

      </div>

    </div>

  );
}


// =========================================================
// INFO CARD
// =========================================================

function InfoCard({
  title,
  value,
}) {

  return (

    <div className="rounded-xl bg-slate-950 p-4">

      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
        {title}
      </p>

      <p className="mt-2 text-sm leading-6 text-slate-300">
        {value || "Not provided"}
      </p>

    </div>

  );

}


export default App;