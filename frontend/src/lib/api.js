import axios from "axios";

const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  "https://fantasy-jq2t.onrender.com";

export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export function extractPlayers(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.players)) return data.players;
  return [];
}
