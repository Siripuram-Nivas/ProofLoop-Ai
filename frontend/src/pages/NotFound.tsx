import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Brand } from "../components/Brand";

export function NotFound() {
  useEffect(() => {
    document.title = "Page not found — ProofLoop AI";
  }, []);

  return (
    <div className="grid min-h-screen place-items-center bg-surface px-5">
      <div className="text-center">
        <Brand className="justify-center" />
        <p className="eyebrow mt-10">404</p>
        <h1 className="display mt-3 text-5xl text-ink">This trail ends here.</h1>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-ink-soft">
          The page you asked for does not exist. No evidence was found for it, and we will not invent any.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex h-11 items-center gap-2 rounded-xl bg-ink px-5 text-sm font-medium text-white"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Back to ProofLoop
        </Link>
      </div>
    </div>
  );
}
