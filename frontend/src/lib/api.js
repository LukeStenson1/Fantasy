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

export const POSITION_STYLES = {
  QB: "bg-red-50 text-red-700 border-red-200",
  RB: "bg-blue-50 text-blue-700 border-blue-200",
  WR: "bg-emerald-50 text-emerald-700 border-emerald-200",
  TE: "bg-amber-50 text-amber-700 border-amber-200",
  K: "bg-pink-50 text-pink-700 border-pink-200",
  DEF: "bg-slate-100 text-slate-700 border-slate-300",
};

export const TAG_STYLES = {
  elite: "bg-black text-white border-black",
  breakout: "bg-emerald-600 text-white border-emerald-600",
  sleeper: "bg-blue-600 text-white border-blue-600",
  risk: "bg-red-600 text-white border-red-600",
};

export const TAG_LABELS = {
  elite: "ELITE",
  breakout: "BREAKOUT",
  sleeper: "SLEEPER",
  risk: "BUST RISK",
};
