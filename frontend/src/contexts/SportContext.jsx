import { createContext, useContext, useState } from "react";

const SportContext = createContext(null);

export function SportProvider({ children }) {
  const [sport, setSport] = useState("nfl");
  return (
    <SportContext.Provider value={{ sport, setSport }}>
      {children}
    </SportContext.Provider>
  );
}

export function useSport() {
  return useContext(SportContext);
}
