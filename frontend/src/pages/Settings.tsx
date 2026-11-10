import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Database,
  FileSearch,
  KeyRound,
  LogOut,
  ScanText,
  ShieldCheck,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { HealthInfo } from "../lib/types";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { Button, Card, InlineAlert, Skeleton } from "../components/ui";

const LIMITATIONS = [
  "Research uses Wikipedia, a community-edited tertiary source. Verify consequential claims against primary sources.",
  "Only the top excerpts per claim are evaluated; absence of a conflict does not prove consistency.",
  "Claim extraction is capped at 8 atomic claims per run.",
  "Screenshot OCR is not enabled. The upload route refuses images rather than inventing text.",
  "Guest workspaces live in this browser session. Create an account to keep future history across devices.",
  "There is no data-deletion UI in this version. The SQLite database is the source of truth and should be backed up as a file.",
];

export function Settings() {
  const { user, signOut } = useAuth();
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load API capabilities."));
  }, []);

  const leave = async () => {
    setBusy(true);
    try {
      await signOut();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="eyebrow">Settings</p>
        <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Workspace &amp; capabilities.</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          What this deployment can actually do. No switches that pretend to enable missing infrastructure.
        </p>
      </div>

      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center gap-2">
            {user?.is_guest ? <UserRound className="size-4" aria-hidden /> : <KeyRound className="size-4" aria-hidden />}
            <h2 className="text-sm font-semibold text-ink">Account</h2>
          </div>
          <dl className="mt-4 space-y-2.5 text-[12px]">
            <div className="flex justify-between gap-4">
              <dt className="text-ink-soft">Type</dt>
              <dd className="font-medium text-ink">{user?.is_guest ? "Guest workspace" : "Email account"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-soft">Identity</dt>
              <dd className="truncate font-medium text-ink">{user?.email || user?.id}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-soft">Created</dt>
              <dd className="font-medium text-ink">{formatDate(user?.created_at)}</dd>
            </div>
          </dl>
          <div className="mt-5 flex flex-wrap gap-2">
            {user?.is_guest ? (
              <Link to="/auth">
                <Button size="sm">Sign in or create an account</Button>
              </Link>
            ) : (
              <Button size="sm" variant="secondary" icon={LogOut} onClick={() => void leave()} loading={busy}>
                Sign out
              </Button>
            )}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-soft">
            {user?.is_guest
              ? "Signing in opens a different account workspace. Runs made as a guest are not migrated automatically."
              : "Signing out returns this browser to a new guest workspace. Your account data stays stored."}
          </p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2">
            <ScanText className="size-4" aria-hidden />
            <h2 className="text-sm font-semibold text-ink">Active engines</h2>
          </div>
          {health ? (
            <dl className="mt-4 space-y-2.5 text-[12px]">
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">Research provider</dt>
                <dd className="font-medium capitalize text-ink">{health.research}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">Claim extraction</dt>
                <dd className="font-medium capitalize text-ink">{health.extraction}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">Storage</dt>
                <dd className="font-medium uppercase text-ink">{health.storage}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">Screenshot OCR</dt>
                <dd className="font-medium text-ink">{health.image_ocr ? "Enabled" : "Not enabled"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">Environment</dt>
                <dd className="font-medium capitalize text-ink">{health.environment}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-soft">API version</dt>
                <dd className="font-medium text-ink">{health.version}</dd>
              </div>
            </dl>
          ) : (
            <Skeleton className="mt-4 h-36" />
          )}
          <p className="mt-3 text-[11px] leading-relaxed text-ink-soft">
            LLM-assisted extraction is used only when a server-side key is configured. It never supplies
            evidence, URLs, or verdicts.
          </p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4" aria-hidden />
            <h2 className="text-sm font-semibold text-ink">Methodology</h2>
          </div>
          <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-[12px] leading-relaxed text-ink-soft">
            <li>Original input is preserved verbatim.</li>
            <li>Claims are split and independently researched.</li>
            <li>Excerpts are stored with URL, publisher, and retrieval time.</li>
            <li>Numbers and years are compared deterministically (1% support tolerance, 5% conflict threshold).</li>
            <li>Verdicts are aggregated conservatively; missing evidence stays missing.</li>
            <li>Conflicts and limitations are written into the report snapshot.</li>
          </ol>
          <Link to="/app/new" className="mt-4 inline-flex items-center gap-1 text-[12px] font-medium text-powder-deep hover:underline">
            See it on a real claim
          </Link>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2">
            <Database className="size-4" aria-hidden />
            <h2 className="text-sm font-semibold text-ink">Data &amp; privacy</h2>
          </div>
          <ul className="mt-3 space-y-2 text-[12px] leading-relaxed text-ink-soft">
            <li>Inputs, claims, and evidence snapshots are stored in the workspace database.</li>
            <li>API keys stay server-side; none are exposed to this page or the browser bundle.</li>
            <li>Outbound requests are limited to source retrieval, URL ingestion, and optional LLM extraction.</li>
            <li>Uploads are capped at 10 MB and private/reserved network targets are blocked.</li>
          </ul>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-2">
          <TriangleAlert className="size-4 text-caution" aria-hidden />
          <h2 className="text-sm font-semibold text-ink">Known limitations</h2>
        </div>
        <ul className="mt-3 grid gap-2 text-[12px] leading-relaxed text-ink-soft md:grid-cols-2">
          {LIMITATIONS.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-ink-soft/50" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap gap-3 text-[11px]">
          <a
            href="/api/v1/health"
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 font-medium text-powder-deep hover:underline"
          >
            <FileSearch className="size-3" aria-hidden />
            API health
          </a>
          <a
            href="https://www.mediawiki.org/wiki/API:Main_page"
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 font-medium text-powder-deep hover:underline"
          >
            Research API documentation
          </a>
        </div>
      </Card>
    </div>
  );
}
