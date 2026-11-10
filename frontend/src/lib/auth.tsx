import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  retry: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.me();
      setUser(result.user);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
        try {
          const guest = await api.guest();
          setUser(guest.user);
        } catch (guestError) {
          setError(
            guestError instanceof Error
              ? guestError.message
              : "Could not start a workspace session.",
          );
        }
      } else {
        setError(err instanceof Error ? err.message : "Could not reach the ProofLoop API.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    setUser(result.user);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const result = await api.register(email, password);
    setUser(result.user);
  }, []);

  const signOut = useCallback(async () => {
    await api.logout().catch(() => undefined);
    const guest = await api.guest();
    setUser(guest.user);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, signIn, register, signOut, retry: bootstrap }),
    [user, loading, error, signIn, register, signOut, bootstrap],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
