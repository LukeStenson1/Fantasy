import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { formatApiErrorDetail } from "../lib/api";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email, password);
      navigate("/my-rankings");
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e16] flex flex-col">
      <div className="flex-1 flex items-center justify-center px-4 py-12 bg-grid">
        <div className="w-full max-w-md">
          <Link to="/" className="flex items-center gap-2 mb-8" data-testid="login-logo">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <div className="absolute inset-0 bg-emerald-500 rotate-[3deg]"></div>
              <div className="absolute inset-0 bg-slate-950 border border-emerald-500/60"></div>
              <span className="relative font-display font-black text-base text-emerald-400">FL</span>
            </div>
            <div className="font-display font-black text-xl text-white">Fantasy<span className="text-emerald-400">Lab</span></div>
          </Link>
          <h1 className="font-display text-3xl font-black text-white mb-1" data-testid="login-title">Welcome back</h1>
          <p className="text-slate-400 mb-8 text-sm">Sign in to save custom rankings and Lab analyses.</p>

          <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Email</label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoFocus className="bg-slate-900 border-slate-700 text-white" data-testid="login-email-input" />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Password</label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required className="bg-slate-900 border-slate-700 text-white" data-testid="login-password-input" />
            </div>
            {error && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-md px-3 py-2" data-testid="login-error">{error}</div>}
            <Button type="submit" disabled={loading} className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold h-11" data-testid="login-submit-btn">
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="text-sm text-slate-400 mt-6">
            Don't have an account? <Link to="/register" className="font-semibold text-emerald-400 hover:underline" data-testid="login-to-register-link">Sign up</Link>
          </p>
          <p className="text-xs text-slate-600 mt-8 font-mono-tab">Demo: admin@ffref.com / admin123</p>
        </div>
      </div>
    </div>
  );
}
