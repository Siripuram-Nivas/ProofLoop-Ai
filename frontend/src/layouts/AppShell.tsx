import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  FileText,
  History,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  Network,
  Plus,
  Radar,
  Settings,
  UserRound,
  X,
} from "lucide-react";
import { Brand } from "../components/Brand";
import { useAuth } from "../lib/auth";
import { Button, cn } from "../components/ui";

const NAV = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/new", label: "New verification", icon: Plus },
  { to: "/app/history", label: "History", icon: History },
  { to: "/app/graph", label: "Evidence graph", icon: Network },
  { to: "/app/radar", label: "Contradiction radar", icon: Radar },
  { to: "/app/reports", label: "Reports", icon: FileText },
  { to: "/app/settings", label: "Settings", icon: Settings },
];

function pageTitle(pathname: string): string {
  if (pathname.startsWith("/app/verifications/")) return "Verification";
  const found = NAV.find((item) => (item.end ? pathname === item.to : pathname.startsWith(item.to)));
  return found?.label || "Workspace";
}

export function AppShell() {
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  useEffect(() => {
    document.title = `${pageTitle(location.pathname)} — ProofLoop AI`;
  }, [location.pathname]);

  const initials = (user?.email || "Guest").slice(0, 2).toUpperCase();

  const nav = (
    <nav className="space-y-1" aria-label="Workspace">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-colors",
              isActive
                ? "bg-white/10 text-white"
                : "text-white/55 hover:bg-white/[0.06] hover:text-white/90",
            )
          }
        >
          {({ isActive }) => (
            <>
              <span
                className={cn(
                  "grid size-7 place-items-center rounded-lg transition-colors",
                  isActive ? "bg-powder text-ink" : "bg-white/[0.06] text-white/60 group-hover:text-white",
                )}
              >
                <item.icon className="size-3.5" aria-hidden />
              </span>
              {item.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );

  const account = (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <div className="flex items-center gap-2.5">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-lavender text-[11px] font-semibold text-ink">
          {user?.is_guest ? <UserRound className="size-4" aria-hidden /> : initials}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[12px] font-medium text-white">
            {user?.email || "Guest workspace"}
          </p>
          <p className="text-[10px] text-white/45">
            {user?.is_guest ? "Session only · not saved across devices" : "Signed in"}
          </p>
        </div>
      </div>
      {user?.is_guest ? (
        <Link
          to="/auth"
          className="mt-2.5 flex items-center justify-center gap-1.5 rounded-lg border border-white/15 py-1.5 text-[11px] font-medium text-white/80 hover:bg-white/10"
        >
          <LogIn className="size-3" aria-hidden />
          Sign in to keep history
        </Link>
      ) : (
        <button
          type="button"
          onClick={() => void signOut()}
          className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/15 py-1.5 text-[11px] font-medium text-white/80 hover:bg-white/10"
        >
          <LogOut className="size-3" aria-hidden />
          Sign out
        </button>
      )}
    </div>
  );

  const sidebarContent = (
    <div className="flex h-full flex-col bg-ink px-4 py-5">
      <div className="px-1.5">
        <Brand dark />
      </div>
      <div className="mt-7 flex-1 overflow-y-auto">{nav}</div>
      <div className="mt-4 space-y-3">
        <Link
          to="/app/new"
          className="flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-powder px-3 text-[13px] font-semibold text-ink transition-colors hover:bg-[#96c7f4]"
        >
          <Plus className="size-4" aria-hidden />
          New verification
        </Link>
        {account}
        <p className="px-1 text-[9px] leading-relaxed text-white/30">
          Evidence is retrieved live. ProofLoop never invents a source or a verdict.
        </p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-surface">
      <a
        href="#workspace-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-ink"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] lg:block">{sidebarContent}</aside>

      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-ink/50 backdrop-blur-sm"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-[280px] shadow-2xl">
            <button
              type="button"
              className="absolute right-3 top-4 z-10 grid size-8 place-items-center rounded-lg text-white/70 hover:bg-white/10"
              onClick={() => setOpen(false)}
              aria-label="Close navigation"
            >
              <X className="size-4" aria-hidden />
            </button>
            {sidebarContent}
          </div>
        </div>
      ) : null}

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-20 border-b border-line/80 bg-surface/85 backdrop-blur-lg">
          <div className="flex h-14 items-center gap-3 px-4 md:px-7">
            <button
              type="button"
              className="grid size-9 place-items-center rounded-lg border border-line bg-white text-ink lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
              aria-expanded={open}
            >
              <Menu className="size-4" aria-hidden />
            </button>
            <p className="text-[13px] font-semibold text-ink">{pageTitle(location.pathname)}</p>
            <span className="hidden items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-[10px] text-ink-soft sm:inline-flex">
              <span className="size-1.5 rounded-full bg-support" aria-hidden />
              Live research · {user?.is_guest ? "guest session" : "account"}
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Link
                to="/"
                className="hidden text-[12px] font-medium text-ink-soft hover:text-ink sm:block"
              >
                Public site
              </Link>
              {user?.is_guest ? (
                <Link to="/auth" className="rounded-lg border border-line bg-white px-3 py-1.5 text-[12px] font-medium text-ink hover:border-ink/30">
                  Sign in
                </Link>
              ) : (
                <span className="hidden text-[12px] text-ink-soft md:block">{user?.email}</span>
              )}
            </div>
          </div>
        </header>
        <main id="workspace-main" className="mx-auto w-full max-w-[1180px] px-4 py-7 md:px-7 md:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
