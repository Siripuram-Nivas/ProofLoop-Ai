import type { ReactNode } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Loader2, RefreshCw } from "lucide-react";
import { AuthProvider, useAuth } from "./lib/auth";
import { Brand } from "./components/Brand";
import { AppShell } from "./layouts/AppShell";
import { Landing } from "./pages/Landing";
import { Overview } from "./pages/Overview";
import { NewVerification } from "./pages/NewVerification";
import { History } from "./pages/History";
import { VerificationDetail } from "./pages/VerificationDetail";
import { GraphExplorer } from "./pages/GraphExplorer";
import { RadarPage } from "./pages/Radar";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { Auth } from "./pages/Auth";
import { NotFound } from "./pages/NotFound";

function Splash({ message = "Preparing your workspace…" }: { message?: string }) {
  return (
    <div className="grid min-h-screen place-items-center bg-surface px-5">
      <div className="text-center">
        <Brand className="justify-center" />
        <p className="mt-6 flex items-center justify-center gap-2 text-[12px] text-ink-soft">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          {message}
        </p>
      </div>
    </div>
  );
}

function SessionProblem() {
  const { error, retry } = useAuth();
  return (
    <div className="grid min-h-screen place-items-center bg-surface px-5">
      <div className="max-w-md text-center">
        <Brand className="justify-center" />
        <h1 className="display mt-8 text-4xl text-ink">The API is out of reach.</h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          {error || "Could not start a workspace session."} Start the backend and retry. Nothing is
          simulated while the API is offline.
        </p>
        <button
          type="button"
          onClick={() => void retry()}
          className="mt-6 inline-flex h-11 items-center gap-2 rounded-xl bg-ink px-5 text-sm font-medium text-white"
        >
          <RefreshCw className="size-4" aria-hidden />
          Retry connection
        </button>
      </div>
    </div>
  );
}

function SessionGate({ children }: { children: ReactNode }) {
  const { user, loading, error } = useAuth();
  if (loading) return <Splash />;
  if (error) return <SessionProblem />;
  if (!user) return <Splash message="Starting a guest session…" />;
  return <>{children}</>;
}

function AuthGate() {
  const { loading, error } = useAuth();
  if (loading) return <Splash message="Checking your session…" />;
  if (error) return <SessionProblem />;
  return <Auth />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/auth" element={<AuthGate />} />
          <Route
            path="/app"
            element={
              <SessionGate>
                <AppShell />
              </SessionGate>
            }
          >
            <Route index element={<Overview />} />
            <Route path="new" element={<NewVerification />} />
            <Route path="history" element={<History />} />
            <Route path="verifications/:id" element={<VerificationDetail />} />
            <Route path="graph" element={<GraphExplorer />} />
            <Route path="radar" element={<RadarPage />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
