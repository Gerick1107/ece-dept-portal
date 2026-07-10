import { FormEvent, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";
import { forgotPassword } from "../services/api";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const emailRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);

  if (!loading && user) return <Navigate to="/dashboard" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function onForgotPassword() {
    const input = emailRef.current;
    if (!input) return;
    if (!input.checkValidity()) {
      input.reportValidity();
      return;
    }

    setError("");
    setMessage("");
    setResetting(true);
    try {
      const detail = await forgotPassword(input.value.trim());
      setMessage(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send reset email");
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-teal-900 to-slate-800 px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white rounded-xl shadow-xl p-8 space-y-5"
      >
        <div className="flex flex-col items-center text-center gap-3">
          <img src="/logo.png?v=2" alt="ECE Department" className="h-16 bg-white rounded-lg p-2 shadow" />
          <div>
            <p className="text-xs text-teal-700 font-semibold uppercase tracking-wide">
              ECE Department
            </p>
            <h1 className="text-2xl font-bold text-slate-900">Automation Portal</h1>
            <p className="text-sm text-slate-500 mt-1">Sign in with your institutional account</p>
          </div>
        </div>
        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}
        {message && (
          <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
            {message}
          </p>
        )}
        <label className="block text-sm font-medium text-slate-700">
          Email
          <input
            ref={emailRef}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-teal-700 text-white rounded-lg py-2.5 font-medium hover:bg-teal-600 disabled:opacity-60 transition-colors"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        <button
          type="button"
          disabled={resetting}
          className="w-full text-sm text-teal-700 hover:underline disabled:opacity-60"
          onClick={onForgotPassword}
        >
          {resetting ? "Sending…" : "Forgot password?"}
        </button>
      </form>
    </div>
  );
}
