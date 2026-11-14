import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  FileText,
  Image,
  Link2,
  ScanText,
  Server,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { api, ApiError, type EngineListing, type MomenSession } from "../lib/api";
import { buildMomenSubmission } from "../lib/momen";
import { ENGINE_STATE_LABEL } from "../lib/format";
import type { HealthInfo } from "../lib/types";
import {
  Button,
  Card,
  Field,
  InlineAlert,
  Input,
  Select,
  Textarea,
  cn,
} from "../components/ui";

type Mode = "text" | "document" | "url" | "image";

const EXAMPLE = `The Eiffel Tower is 330 metres tall. It was completed in 1889. The tower is located in Paris, France.`;

const TABS: { id: Mode; label: string; icon: typeof FileText }[] = [
  { id: "text", label: "Paste text", icon: FileText },
  { id: "document", label: "PDF / document", icon: UploadCloud },
  { id: "url", label: "Web page", icon: Link2 },
  { id: "image", label: "Screenshot", icon: Image },
];

export function NewVerification() {
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("text");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [momen, setMomen] = useState<MomenSession | null>(null);
  const [momenEmail, setMomenEmail] = useState("");
  const [momenPassword, setMomenPassword] = useState("");
  const [momenWorkspace, setMomenWorkspace] = useState<number | "">("");
  const [momenBusy, setMomenBusy] = useState(false);
  const [momenError, setMomenError] = useState<string | null>(null);
  const [momenCreated, setMomenCreated] = useState<number | null>(null);
  const [engineList, setEngineList] = useState<EngineListing | null>(null);
  const [claimEngine, setClaimEngine] = useState<"deterministic" | "openai" | "gemini">(
    "deterministic",
  );
  const [researchEngine, setResearchEngine] = useState<"wikipedia" | "google_search">(
    "wikipedia",
  );
  const [analysisEngine, setAnalysisEngine] = useState<"" | "openai" | "gemini">("");
  const [reviewEngine, setReviewEngine] = useState<"" | "openai" | "gemini">("");

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.engines().then(setEngineList).catch(() => setEngineList(null));
  }, []);

  useEffect(() => {
    api
      .momenSession()
      .then((next) => {
        setMomen(next);
        if (next.workspaces.length) setMomenWorkspace(next.workspaces[0].id);
      })
      .catch(() =>
        setMomen({
          connected: false,
          workspaces: [],
          read_access: false,
          persistence_available: false,
        }),
      );
  }, []);

  const connectMomen = async () => {
    if (!momenEmail.trim() || !momenPassword || momenBusy) return;
    setMomenBusy(true);
    setMomenError(null);
    setMomenCreated(null);
    try {
      const next = await api.momenLogin(momenEmail.trim(), momenPassword);
      setMomen(next);
      setMomenPassword("");
      if (next.workspaces.length) setMomenWorkspace(next.workspaces[0].id);
    } catch (err) {
      setMomenError(
        err instanceof ApiError ? err.message : "Could not connect to Momen.",
      );
    } finally {
      setMomenBusy(false);
    }
  };

  const disconnectMomen = async () => {
    await api.momenLogout().catch(() => undefined);
    setMomen({
      connected: false,
      workspaces: [],
      read_access: false,
      persistence_available: false,
    });
    setMomenWorkspace("");
    setMomenCreated(null);
  };

  const sendToMomen = async () => {
    if (!momenWorkspace || momenBusy) {
      setMomenError("Choose a Momen workspace first.");
      return;
    }
    const body = buildMomenSubmission({
      workspaceId: momenWorkspace,
      mode,
      title,
      text,
      url,
    });
    if (!body) {
      setMomenError("Momen import supports pasted text and web URLs right now.");
      return;
    }
    setMomenBusy(true);
    setMomenError(null);
    setMomenCreated(null);
    try {
      const created = await api.momenCreateVerification(body);
      setMomenCreated(created.verification_job_id);
    } catch (err) {
      setMomenError(
        err instanceof ApiError ? err.message : "Could not create the Momen job.",
      );
    } finally {
      setMomenBusy(false);
    }
  };

  const canSubmit =
    mode === "text"
      ? text.trim().length >= 20
      : mode === "document"
        ? Boolean(file)
        : mode === "url"
          ? /^https?:\/\/.+/i.test(url.trim())
          : false;

  const ready = (id: "openai" | "gemini" | "google_search") =>
    engineList?.engines.find((engine) => engine.id === id)?.available ?? false;

  const stateSuffix = (id: "openai" | "gemini" | "google_search") => {
    const engine = engineList?.engines.find((item) => item.id === id);
    if (!engine || engine.available) return "";
    return ` (${ENGINE_STATE_LABEL[engine.state || "unavailable"] || "Unavailable"})`;
  };

  const acceptFile = (candidate: File | null) => {
    setError(null);
    if (!candidate) return;
    const extension = candidate.name.toLowerCase().split(".").pop() || "";
    if (!["pdf", "txt", "md", "text"].includes(extension)) {
      setError("Unsupported file. Use a PDF or a plain text file (.txt, .md).");
      return;
    }
    if (candidate.size > 10 * 1024 * 1024) {
      setError("That file is larger than the 10 MB limit.");
      return;
    }
    setFile(candidate);
  };

  const submit = async () => {
    if (!canSubmit || submitting) return;
    setError(null);
    setSubmitting(true);
    const engines = {
      claim_extraction: claimEngine,
      research: researchEngine,
      analysis: analysisEngine,
      review: reviewEngine,
    };
    try {
      let uploadId: string | undefined;
      if (mode === "document" && file) {
        setStatus("Extracting text from the document…");
        const upload = await api.upload(file);
        uploadId = upload.id;
      }
      setStatus("Creating the verification…");
      const created =
        mode === "text"
          ? await api.createVerification({
              text: text.trim(),
              title: title.trim() || undefined,
              engines,
            })
          : mode === "url"
            ? await api.createVerification({
                url: url.trim(),
                title: title.trim() || undefined,
                engines,
              })
            : await api.createVerification({
                upload_id: uploadId,
                title: title.trim() || undefined,
                engines,
              });
      navigate(`/app/verifications/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the verification.");
      setStatus("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="eyebrow">New verification</p>
        <h1 className="display mt-2 text-4xl text-ink md:text-5xl">What should we check?</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          The original input is stored verbatim. Claims are extracted from it, and every conclusion in
          the report will point back to a retrieved source.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.5fr_0.8fr]">
        <Card className="overflow-hidden">
          <div className="flex gap-1 overflow-x-auto border-b border-line p-3">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setMode(tab.id);
                  setError(null);
                }}
                aria-pressed={mode === tab.id}
                className={cn(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-[12px] font-medium transition-colors",
                  mode === tab.id ? "bg-ink text-white" : "text-ink-soft hover:bg-lavender/60",
                )}
              >
                <tab.icon className="size-3.5" aria-hidden />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="space-y-5 p-5 md:p-6">
            {mode === "text" ? (
              <>
                <Field
                  label="Claim or passage"
                  htmlFor="verification-text"
                  hint={`${text.length.toLocaleString()} / 200,000`}
                >
                  <Textarea
                    id="verification-text"
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    placeholder="Paste a statement, an article extract, or a document passage containing factual claims…"
                    className="min-h-48"
                  />
                </Field>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setText(EXAMPLE);
                      setTitle("Eiffel Tower fact check");
                    }}
                  >
                    Load example input
                  </Button>
                  <span className="text-[11px] text-ink-soft">
                    The example only fills the input. Research results are always live.
                  </span>
                </div>
              </>
            ) : null}

            {mode === "document" ? (
              <>
                <div
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragging(false);
                    acceptFile(event.dataTransfer.files?.[0] || null);
                  }}
                  className={cn(
                    "rounded-2xl border-2 border-dashed p-8 text-center transition-colors",
                    dragging ? "border-powder-deep bg-[#F1F8FE]" : "border-line bg-surface/50",
                  )}
                >
                  <UploadCloud className="mx-auto size-7 text-ink-soft" aria-hidden />
                  <p className="mt-3 text-sm font-medium text-ink">
                    {file ? file.name : "Drop a PDF or text file here"}
                  </p>
                  <p className="mt-1 text-[11px] text-ink-soft">
                    PDF, TXT, MD · 10 MB max · text is extracted server-side
                  </p>
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".pdf,.txt,.md,text/plain,application/pdf"
                    className="sr-only"
                    onChange={(event) => acceptFile(event.target.files?.[0] || null)}
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    className="mt-4"
                    onClick={() => fileInput.current?.click()}
                  >
                    Choose file
                  </Button>
                </div>
                <InlineAlert tone="info">
                  Scanned PDFs contain images, not selectable text. If extraction finds no readable text,
                  the run stops with an explanation instead of guessing. Screenshot OCR is not enabled in
                  this deployment.
                </InlineAlert>
              </>
            ) : null}

            {mode === "url" ? (
              <>
                <Field label="Public page URL" htmlFor="verification-url" hint="http:// or https://">
                  <Input
                    id="verification-url"
                    type="url"
                    value={url}
                    onChange={(event) => setUrl(event.target.value)}
                    placeholder="https://example.org/report"
                  />
                </Field>
                <InlineAlert tone="info">
                  The page is fetched server-side as HTML or text. Private network addresses, credentialed
                  URLs, and redirects are rejected. The extracted text is stored as the original input.
                </InlineAlert>
              </>
            ) : null}

            {mode === "image" ? (
              <InlineAlert tone="warn">
                <strong>Screenshot upload needs OCR, which is not enabled here.</strong> ProofLoop will not
                invent text from an image. Use the PDF or paste the text shown in the screenshot instead.
              </InlineAlert>
            ) : null}

            {mode !== "image" ? (
              <Field label="Title" htmlFor="verification-title" optional>
                <Input
                  id="verification-title"
                  value={title}
                  maxLength={160}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Eiffel Tower fact check"
                />
              </Field>
            ) : null}

            {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
            {status ? (
              <p className="flex items-center gap-2 text-[12px] text-ink-soft" aria-live="polite">
                <span className="size-1.5 animate-pulse rounded-full bg-powder-deep" aria-hidden />
                {status}
              </p>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={() => void submit()}
                disabled={!canSubmit}
                loading={submitting}
                icon={ArrowRight}
              >
                Extract claims &amp; verify
              </Button>
              <span className="text-[11px] text-ink-soft">
                Up to 8 claims per run · research usually takes 5–20 seconds
              </span>
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
              <ShieldCheck className="size-4" aria-hidden />
              What happens next
            </h2>
            <ol className="mt-4 space-y-3">
              {[
                ["Input preserved", "The exact submitted text is kept with the job."],
                ["Claims extracted", "Compound sentences are split into checkable statements."],
                ["Live research", "Public sources are retrieved with real URLs and timestamps."],
                ["Evidence evaluated", "Numbers and dates compared with documented tolerances."],
                ["Conflicts checked", "Disagreements are recorded, not silently resolved."],
                ["Report generated", "Findings, sources, and limitations in one snapshot."],
              ].map(([title, body], index) => (
                <li key={title} className="flex gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full border border-line bg-white text-[10px] font-semibold text-ink">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-[12px] font-semibold text-ink">{title}</p>
                    <p className="text-[11px] leading-relaxed text-ink-soft">{body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
              <Bot className="size-4 text-powder-deep" aria-hidden />
              AI engines
            </h2>
            <p className="mt-2 text-[11px] leading-relaxed text-ink-soft">
              Optional. Providers that are not configured on the server cannot be selected. If the chosen
              provider runs out of quota or has a temporary outage, the server tries the next configured
              provider and records which one answered.
            </p>
            <div className="mt-3 space-y-3">
              <Field label="Claim extraction" htmlFor="engine-extraction">
                <Select
                  id="engine-extraction"
                  value={claimEngine}
                  onChange={(event) =>
                    setClaimEngine(event.target.value as typeof claimEngine)
                  }
                >
                  <option value="deterministic">Deterministic (local)</option>
                  <option value="openai" disabled={!ready("openai")}>
                    OpenAI{stateSuffix("openai")}
                  </option>
                  <option value="gemini" disabled={!ready("gemini")}>
                    Gemini{stateSuffix("gemini")}
                  </option>
                </Select>
              </Field>
              <Field label="Research" htmlFor="engine-research">
                <Select
                  id="engine-research"
                  value={researchEngine}
                  onChange={(event) =>
                    setResearchEngine(event.target.value as typeof researchEngine)
                  }
                >
                  <option value="wikipedia">Wikipedia (deterministic)</option>
                  <option value="google_search" disabled={!ready("google_search")}>
                    Google Search via Gemini{stateSuffix("google_search")}
                  </option>
                </Select>
              </Field>
              <Field label="Evidence analysis" htmlFor="engine-analysis">
                <Select
                  id="engine-analysis"
                  value={analysisEngine}
                  onChange={(event) =>
                    setAnalysisEngine(event.target.value as typeof analysisEngine)
                  }
                >
                  <option value="">Off</option>
                  <option value="openai" disabled={!ready("openai")}>
                    OpenAI{stateSuffix("openai")}
                  </option>
                  <option value="gemini" disabled={!ready("gemini")}>
                    Gemini{stateSuffix("gemini")}
                  </option>
                </Select>
              </Field>
              <Field label="Independent review" htmlFor="engine-review">
                <Select
                  id="engine-review"
                  value={reviewEngine}
                  onChange={(event) =>
                    setReviewEngine(event.target.value as typeof reviewEngine)
                  }
                >
                  <option value="">Off</option>
                  <option value="openai" disabled={!ready("openai")}>
                    OpenAI{stateSuffix("openai")}
                  </option>
                  <option value="gemini" disabled={!ready("gemini")}>
                    Gemini{stateSuffix("gemini")}
                  </option>
                </Select>
              </Field>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-ink-soft">
              Model output is recorded as a recommendation. It never changes the deterministic verdict
              or the stored excerpts.
            </p>
          </Card>

          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
              <Server className="size-4 text-powder-deep" aria-hidden />
              Momen backend
            </h2>
            {momen?.connected ? (
              <div className="mt-3 space-y-3">
                <p className="text-[12px] text-ink-soft">
                  Connected as{" "}
                  <span className="font-medium text-ink">
                    {momen.account?.email || momen.account?.username || "Momen account"}
                  </span>
                </p>
                {momen.workspaces.length ? (
                  <Field label="Workspace" htmlFor="momen-workspace">
                    <Select
                      id="momen-workspace"
                      value={momenWorkspace}
                      onChange={(event) => {
                        setMomenWorkspace(
                          event.target.value ? Number(event.target.value) : "",
                        );
                        setMomenCreated(null);
                      }}
                    >
                      {momen.workspaces.map((workspace) => (
                        <option key={workspace.id} value={workspace.id}>
                          {workspace.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                ) : (
                  <InlineAlert tone="warn">
                    No Momen workspace could be listed. Server read access may not be
                    configured.
                  </InlineAlert>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void sendToMomen()}
                  loading={momenBusy}
                  disabled={!momenWorkspace || (mode !== "text" && mode !== "url")}
                >
                  Send input to Momen
                </Button>
                <p className="text-[11px] leading-relaxed text-ink-soft">
                  Creates a real Momen verification job with your Momen user token.
                  Result persistence stays unavailable until PersistVerificationPackage
                  is deployed.
                </p>
                {mode !== "text" && mode !== "url" ? (
                  <p className="text-[11px] leading-relaxed text-ink-soft">
                    Momen file upload is not wired yet, so PDF and image inputs cannot
                    be sent from here.
                  </p>
                ) : null}
                {momenCreated ? (
                  <InlineAlert tone="success">
                    Momen job #{momenCreated} created. Result persistence is not
                    available yet.
                  </InlineAlert>
                ) : null}
                <Button size="sm" variant="ghost" onClick={() => void disconnectMomen()}>
                  Disconnect
                </Button>
              </div>
            ) : (
              <div className="mt-3 space-y-3">
                <p className="text-[12px] leading-relaxed text-ink-soft">
                  Sign in to an existing Momen account. No Momen account is created and
                  local ProofLoop accounts are unchanged.
                </p>
                <Field label="Momen email" htmlFor="momen-email">
                  <Input
                    id="momen-email"
                    type="email"
                    autoComplete="username"
                    value={momenEmail}
                    onChange={(event) => setMomenEmail(event.target.value)}
                  />
                </Field>
                <Field label="Momen password" htmlFor="momen-password">
                  <Input
                    id="momen-password"
                    type="password"
                    autoComplete="current-password"
                    value={momenPassword}
                    onChange={(event) => setMomenPassword(event.target.value)}
                  />
                </Field>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void connectMomen()}
                  loading={momenBusy}
                  disabled={!momenEmail.trim() || !momenPassword}
                >
                  Connect Momen
                </Button>
              </div>
            )}
            {momenError ? (
              <InlineAlert tone="error" className="mt-3">
                {momenError}
              </InlineAlert>
            ) : null}
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2">
              <ScanText className="size-4 text-powder-deep" aria-hidden />
              <h2 className="text-sm font-semibold text-ink">Active engines</h2>
            </div>
            {health ? (
              <ul className="mt-3 space-y-2 text-[12px]">
                <li className="flex justify-between gap-3">
                  <span className="text-ink-soft">Research</span>
                  <span className="font-medium capitalize text-ink">{health.research}</span>
                </li>
                <li className="flex justify-between gap-3">
                  <span className="text-ink-soft">Claim extraction</span>
                  <span className="font-medium capitalize text-ink">{health.extraction}</span>
                </li>
                <li className="flex justify-between gap-3">
                  <span className="text-ink-soft">Screenshot OCR</span>
                  <span className="font-medium text-ink">{health.image_ocr ? "Enabled" : "Not enabled"}</span>
                </li>
                <li className="flex justify-between gap-3">
                  <span className="text-ink-soft">Storage</span>
                  <span className="font-medium text-ink">{health.storage}</span>
                </li>
              </ul>
            ) : (
              <p className="mt-3 text-[12px] text-ink-soft">Capabilities unavailable while the API is offline.</p>
            )}
            <p className="mt-3 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-soft">
              <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-support" aria-hidden />
              No sample evidence is inserted into a live run.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
