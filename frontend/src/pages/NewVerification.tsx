import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Image,
  Link2,
  ScanText,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { HealthInfo } from "../lib/types";
import { Button, Card, Field, InlineAlert, Input, Textarea, cn } from "../components/ui";

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

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const canSubmit =
    mode === "text"
      ? text.trim().length >= 20
      : mode === "document"
        ? Boolean(file)
        : mode === "url"
          ? /^https?:\/\/.+/i.test(url.trim())
          : false;

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
          ? await api.createVerification({ text: text.trim(), title: title.trim() || undefined })
          : mode === "url"
            ? await api.createVerification({ url: url.trim(), title: title.trim() || undefined })
            : await api.createVerification({ upload_id: uploadId, title: title.trim() || undefined });
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
