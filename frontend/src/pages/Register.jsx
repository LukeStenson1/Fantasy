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
    <div className="min-h-screen bg-white flex flex-col">
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="block mb-8 font-display font-black text-2xl tracking-tight" data-testid="register-logo">
            FantasyRef<span className="text-emerald-600">.</span>
          </Link>
          <h1 className="font-display text-3xl font-black mb-1" data-testid="register-title">Create your account</h1>
          <p className="text-slate-600 mb-8 text-sm">Save rankings, build lineups, track your league.</p>

          <form onSubmit={onSubmit} className="space-y-4" data-testid="register-form">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required data-testid="register-name-input" />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Email</label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required data-testid="register-email-input" />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">Password</label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={6} data-testid="register-password-input" />
            </div>
            {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2" data-testid="register-error">{error}</div>}
            <Button type="submit" disabled={loading} className="w-full bg-black hover:bg-slate-800 text-white h-11" data-testid="register-submit-btn">
              {loading ? "Creating…" : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-slate-600 mt-6">
            Already have an account? <Link to="/login" className="font-semibold text-black underline" data-testid="register-to-login-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
