import { createContext, useContext, useState } from "react";

const SportContext = createContext(null);

export const SPORT_CONFIG = {
  nfl: {
    label: "NFL",
    accentColor: "text-emerald-400",
    accentBg: "bg-emerald-500",
    accentHover: "hover:bg-emerald-400",
    accentBorder: "border-emerald-500",
    badgeBg: "bg-emerald-500/15",
    badgeText: "text-emerald-300",
    badgeBorder: "border-emerald-500/40",
    hex: "#10b981",
    hexLight: "#34d399",
    hexAlpha: "#10b98120",
    hexBorder: "#10b98166",
  },
  nba: {
    label: "NBA",
    accentColor: "text-orange-400",
    accentBg: "bg-orange-500",
    accentHover: "hover:bg-orange-400",
    accentBorder: "border-orange-500",
    badgeBg: "bg-orange-500/15",
    badgeText: "text-orange-300",
    badgeBorder: "border-orange-500/40",
    hex: "#f97316",
    hexLight: "#fb923c",
    hexAlpha: "#f9731620",
    hexBorder: "#f9731666",
  },
  mlb: {
    label: "MLB",
    accentColor: "text-[#4f8ef7]",
    accentBg: "bg-[#4f8ef7]",
    accentHover: "hover:bg-[#6aa0f8]",
    accentBorder: "border-[#4f8ef7]",
    badgeBg: "bg-[#4f8ef7]/15",
    badgeText: "text-[#7aacf9]",
    badgeBorder: "border-[#4f8ef7]/40",
    hex: "#4f8ef7",
    hexLight: "#7aacf9",
    hexAlpha: "#4f8ef720",
    hexBorder: "#4f8ef766",
  },
};

export function SportProvider({ children }) {
  const [sport, setSport] = useState("nfl");
  const config = SPORT_CONFIG[sport] || SPORT_CONFIG.nfl;
  return (
    <SportContext.Provider value={{ sport, setSport, config }}>
      {children}
    </SportContext.Provider>
  );
}

export function useSport() {
  return useContext(SportContext);
}
