import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { formatApiErrorDetail } from "../lib/api";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(email, password, name);
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
          <Link to="/" className="flex items-center gap-2 mb-8" data-testid="register-logo">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <div className="absolute inset-0 bg-emerald-500 rotate-[3deg]"></div>
              <div className="absolute inset-0 bg-slate-950 border border-emerald-500/60"></div>
              <span className="relative font-display font-black text-base text-emerald-400">FL</span>
            </div>
            <div className="font-display font-black text-xl text-white">Fantasy<span className="text-emerald-400">Lab</span></div>
          </Link>
          <h1 className="font-display text-3xl font-black text-white mb-1" data-testid="register-title">Create your account</h1>
          <p className="text-slate-400 mb-8 text-sm">Save rankings, run Lab analyses, track your league.</p>

          <form onSubmit={onSubmit} className="space-y-4" data-testid="register-form">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required className="bg-slate-900 border-slate-700 text-white" data-testid="register-name-input" />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Email</label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required className="bg-slate-900 border-slate-700 text-white" data-testid="register-email-input" />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 block mb-1.5">Password</label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={6} className="bg-slate-900 border-slate-700 text-white" data-testid="register-password-input" />
            </div>
            {error && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-md px-3 py-2" data-testid="register-error">{error}</div>}
            <Button type="submit" disabled={loading} className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold h-11" data-testid="register-submit-btn">
              {loading ? "Creating…" : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-slate-400 mt-6">
            Already have an account? <Link to="/login" className="font-semibold text-emerald-400 hover:underline" data-testid="register-to-login-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
