import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { Toaster } from "./components/ui/sonner";
import Home from "./pages/Home";
import Stats from "./pages/Stats";
import PlayerProfile from "./pages/PlayerProfile";
import SleepersBusts from "./pages/SleepersBusts";
import Login from "./pages/Login";
import Register from "./pages/Register";
import MyRankings from "./pages/MyRankings";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/player/:id" element={<PlayerProfile />} />
            <Route path="/sleepers-busts" element={<SleepersBusts />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/my-rankings" element={<MyRankings />} />
          </Routes>
          <Toaster position="top-right" />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
