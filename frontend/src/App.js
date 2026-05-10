import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { Toaster } from "./components/ui/sonner";
import Home from "./pages/Home";
import Stats from "./pages/Stats";
import SleepersBusts from "./pages/SleepersBusts";
import Login from "./pages/Login";
import Register from "./pages/Register";
import MyRankings from "./pages/MyRankings";
import Lineup from "./pages/Lineup";
import Rookies from "./pages/Rookies";
import Trades from "./pages/Trades";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/this-week" element={<Navigate to="/" replace />} />
            <Route path="/lineup" element={<Lineup />} />
            <Route path="/start-sit" element={<Navigate to="/lineup" replace />} />
            <Route path="/trades" element={<Trades />} />
            <Route path="/sleepers-busts" element={<SleepersBusts />} />
            <Route path="/rookies" element={<Rookies />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/my-rankings" element={<MyRankings />} />
          </Routes>
          <Toaster position="top-right" theme="dark" />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
