import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import { ArcoinMascot, ArcSymbol } from "../Mascot";

export default function Shell({ children, nav = [], title }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  return (
    <div className="min-h-screen bg-arc">
      <header className="bg-white sticky top-0 z-40" style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.04)" }}>
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-3 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2">
            <ArcoinMascot size={42} />
            <div>
              <div className="font-fredoka font-bold text-xl text-arc-text leading-none">Arcoins</div>
              <div className="text-xs text-arc-muted">{title}</div>
            </div>
          </Link>
          <nav className="hidden md:flex gap-1 bg-arc rounded-full p-1">
            {nav.map((n) => {
              const active = loc.pathname === n.to;
              return (
                <Link key={n.to} to={n.to} data-testid={`nav-${n.key}`} className="px-4 py-2 rounded-full font-semibold text-sm transition-all"
                  style={{ background: active ? "var(--arc-primary)" : "transparent", color: active ? "#fff" : "var(--arc-text)" }}>
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <div className="text-sm font-semibold text-arc-text">{user?.name}</div>
              <div className="text-xs text-arc-muted capitalize">{user?.role === "student" ? "aluno" : user?.role === "teacher" ? "professor" : "admin"}</div>
            </div>
            {user?.avatar && <img src={user.avatar} alt="" className="w-10 h-10 rounded-full bg-arc border-2" style={{ borderColor: "var(--arc-primary)" }} />}
            <button data-testid="logout-btn" onClick={logout} className="arc-btn arc-btn-outline text-sm py-2 px-4">Sair</button>
          </div>
        </div>
        <nav className="md:hidden flex gap-1 px-2 pb-2 overflow-x-auto">
          {nav.map((n) => {
            const active = loc.pathname === n.to;
            return (
              <Link key={n.to} to={n.to} className="flex-shrink-0 px-4 py-2 rounded-full font-semibold text-xs"
                style={{ background: active ? "var(--arc-primary)" : "#F0F8FF", color: active ? "#fff" : "var(--arc-text)" }}>
                {n.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-6 md:py-8">{children}</main>
      <footer className="text-center text-arc-muted text-xs py-6">
        Arcoins © {new Date().getFullYear()} · Protótipo educacional · <ArcSymbol /> Arc é moeda fictícia
      </footer>
    </div>
  );
}
