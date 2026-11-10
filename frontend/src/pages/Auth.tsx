import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, ShieldCheck } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Brand } from "../components/Brand";
import { Button, Card, Field, InlineAlert, Input } from "../components/ui";

export function Auth() {
  const { user, signIn, register, signOut } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Account — ProofLoop AI";
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await signIn(email.trim(), password);
      else await register(email.trim(), password);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not complete sign in.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface lg:grid lg:grid-cols-[0.95fr_1.05fr]">
      <aside className="relative hidden overflow-hidden bg-ink p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -left-20 top-10 size-96 rounded-full bg-powder/20 blur-3xl" aria-hidden />
        <div className="pointer-events-none absolute -right-10 bottom-0 size-72 rounded-full bg-peach/20 blur-3xl" aria-hidden />
        <div className="relative">
          <Brand dark />
        </div>
        <div className="relative max-w-md">
          <p className="eyebrow text-powder/80">Your evidence trail</p>
          <h1 className="display mt-4 text-5xl leading-[1.02]">
            A verdict you cannot trace
            <br />
            <span className="italic text-powder">is just a guess.</span>
          </h1>
          <p className="mt-5 text-sm leading-relaxed text-white/60">
            Sign in to keep future verifications tied to one account, or continue as a guest. Either
            way, the evidence rules are identical.
          </p>
          <ul className="mt-7 space-y-3 text-[13px] text-white/70">
            {[
              "Original input preserved",
              "Real excerpts with URLs and timestamps",
              "Conflicts reported, never auto-resolved",
              "Unverified is never rendered as false",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2.5">
                <span className="grid size-5 place-items-center rounded-full bg-white/10">
                  <Check className="size-3" aria-hidden />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative flex items-center gap-2 text-[11px] text-white/35">
          <ShieldCheck className="size-3.5" aria-hidden />
          Server-side sessions · scrypt password hashing · no third-party identity provider
        </p>
      </aside>

      <main className="flex min-h-screen flex-col">
        <div className="flex items-center justify-between border-b border-line px-5 py-4 lg:hidden">
          <Brand compact />
          <Link to="/" className="text-[12px] font-medium text-ink-soft hover:text-ink">
            Back to site
          </Link>
        </div>
        <div className="flex flex-1 items-center justify-center px-5 py-12">
          <div className="w-full max-w-md">
            {user && !user.is_guest ? (
              <Card className="p-7">
                <p className="eyebrow">Signed in</p>
                <h2 className="display mt-2 text-3xl text-ink">You&rsquo;re already in.</h2>
                <p className="mt-2 text-sm text-ink-soft">
                  This browser is signed in as <strong className="text-ink">{user.email}</strong>.
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                  <Button onClick={() => navigate("/app")} icon={ArrowRight}>
                    Go to workspace
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      await signOut();
                    }}
                  >
                    Sign out
                  </Button>
                </div>
              </Card>
            ) : (
              <>
                <Link
                  to="/"
                  className="mb-6 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-soft hover:text-ink"
                >
                  <ArrowLeft className="size-3.5" aria-hidden />
                  Back to ProofLoop
                </Link>
                <Card className="p-6 md:p-7">
                  <div className="flex gap-1 rounded-xl border border-line bg-surface p-1">
                    {(["login", "register"] as const).map((value) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => {
                          setMode(value);
                          setError(null);
                        }}
                        aria-pressed={mode === value}
                        className={`flex-1 rounded-lg px-3 py-2 text-[12px] font-medium ${
                          mode === value ? "bg-ink text-white" : "text-ink-soft hover:bg-lavender/60"
                        }`}
                      >
                        {value === "login" ? "Sign in" : "Create account"}
                      </button>
                    ))}
                  </div>
                  <h2 className="display mt-5 text-3xl text-ink">
                    {mode === "login" ? "Keep your evidence trail." : "Start a durable workspace."}
                  </h2>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">
                    {mode === "login"
                      ? "Use the email and password you registered with."
                      : "Email and password only. No third-party login, no email verification in this version."}
                  </p>
                  <form className="mt-5 space-y-4" onSubmit={(event) => void submit(event)}>
                    <Field label="Email" htmlFor="auth-email">
                      <Input
                        id="auth-email"
                        type="email"
                        autoComplete="email"
                        required
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="you@example.com"
                      />
                    </Field>
                    <Field
                      label="Password"
                      htmlFor="auth-password"
                      hint={mode === "register" ? "8–128 characters" : undefined}
                    >
                      <Input
                        id="auth-password"
                        type="password"
                        autoComplete={mode === "login" ? "current-password" : "new-password"}
                        required
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="••••••••"
                      />
                    </Field>
                    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
                    <Button type="submit" className="w-full" loading={busy} icon={ArrowRight}>
                      {mode === "login" ? "Sign in" : "Create account"}
                    </Button>
                  </form>
                  <div className="mt-4 border-t border-line pt-4">
                    <p className="text-[11px] leading-relaxed text-ink-soft">
                      Guest workspace runs are tied to this browser session and are not migrated to a new
                      account automatically.
                    </p>
                    <Link to="/app" className="mt-2 inline-flex items-center gap-1 text-[12px] font-medium text-powder-deep hover:underline">
                      Continue as guest
                      <ArrowRight className="size-3" aria-hidden />
                    </Link>
                  </div>
                </Card>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
