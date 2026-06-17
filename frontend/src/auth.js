import React, { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthCtx = createContext(null);

const saved = typeof window !== "undefined" && localStorage.getItem("arc_token");
if (saved) axios.defaults.headers.common["Authorization"] = `Bearer ${saved}`;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    (async () => {
      const t = localStorage.getItem("arc_token");
      if (!t) { setUser(null); return; }
      try {
        const { data } = await axios.get(`${API}/auth/me`);
        setUser(data);
      } catch {
        localStorage.removeItem("arc_token");
        delete axios.defaults.headers.common["Authorization"];
        setUser(null);
      }
    })();
  }, []);

  const login = async (email, password) => {
    const { data } = await axios.post(`${API}/auth/login`, { email, password });
    if (data.token) {
      localStorage.setItem("arc_token", data.token);
      axios.defaults.headers.common["Authorization"] = `Bearer ${data.token}`;
    }
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await axios.post(`${API}/auth/logout`); } catch {}
    localStorage.removeItem("arc_token");
    delete axios.defaults.headers.common["Authorization"];
    setUser(null);
  };

  const refresh = async () => {
    try { const { data } = await axios.get(`${API}/auth/me`); setUser(data); } catch {}
  };

  return <AuthCtx.Provider value={{ user, login, logout, refresh }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
export { API };
