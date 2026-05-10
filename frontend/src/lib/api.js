import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// DARK theme position colors — saturated on dark surface
export const POSITION_STYLES = {
  QB: "bg-red-500/15 text-red-300 border-red-500/40",
  RB: "bg-blue-500/15 text-blue-300 border-blue-500/40",
  WR: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  TE: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  K:  "bg-pink-500/15 text-pink-300 border-pink-500/40",
  DEF:"bg-slate-500/15 text-slate-300 border-slate-500/40",
};

export const TAG_STYLES = {
  elite:    "bg-emerald-500 text-slate-950 border-emerald-500",
  breakout: "bg-emerald-500/20 text-emerald-300 border-emerald-500/50",
  sleeper:  "bg-blue-500/20 text-blue-300 border-blue-500/50",
  risk:     "bg-red-500/20 text-red-300 border-red-500/50",
};

export const TAG_LABELS = {
  elite:    "ELITE",
  breakout: "BREAKOUT",
  sleeper:  "SLEEPER",
  risk:     "BUST RISK",
};
