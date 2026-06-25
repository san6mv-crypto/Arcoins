import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../auth";
import { ArcoinMascot, ArcSymbol } from "../Mascot";

const QUICK_LOGINS = [
  { role: "Aluno", email: "aluno@arcoins.edu", password: "aluno123", color: "#00B4D8", icon: "🎒" },
  { role: "Professor", email: "professor@arcoins.edu", password: "prof123", color: "#06D6A0", icon: "📚" },
  { role: "Admin", email: "admin@arcoins.edu", password: "admin123", color: "#FF006E", icon: "🏫" },
];

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const doLogin = async (e, override) => {
    if (e) e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const creds = override || { email, password };
      const u = await login(creds.email, creds.password);
      const path = u.role === "student" ? "/aluno" : u.role === "teacher" ? "/professor" : "/admin";
      nav(path);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setError(typeof d === "string" ? d : "Erro ao entrar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: "linear-gradient(135deg,#E0F2FE 0%,#F0F8FF 50%,#FFF5D6 100%)" }}>
      <div className="grid md:grid-cols-2 gap-10 max-w-6xl w-full items-center">
        <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6 }} className="text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-4 mb-6">
            <div className="animate-float"><ArcoinMascot size={110} /></div>
            <div>
              <h1 className="font-fredoka text-5xl md:text-6xl font-bold text-arc-text leading-none">Arcoins</h1>
              <p className="font-nunito text-arc-muted mt-2 text-lg">Banco Escolar Digital</p>
            </div>
          </div>
          <p className="font-nunito text-lg md:text-xl text-arc-text/80 max-w-lg">
            Aprenda a <span className="font-bold text-arc-primary">ganhar</span>, <span className="font-bold text-arc-accent">gastar</span> e <span className="font-bold text-arc-success">poupar</span> <ArcSymbol className="text-2xl" /> Arc praticando no dia a dia da escola.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-3 max-w-md">
            {QUICK_LOGINS.map((q) => (
              <motion.button key={q.role} whileHover={{ y: -4 }} whileTap={{ scale: 0.96 }} disabled={loading}
                data-testid={`quick-login-${q.role.toLowerCase()}`}
                onClick={() => doLogin(null, q)}
                className="arc-card p-4 text-center" style={{ borderTop: `4px solid ${q.color}` }}>
                <div className="text-3xl mb-1">{q.icon}</div>
                <div className="font-fredoka font-semibold text-sm text-arc-text">{q.role}</div>
                <div className="text-xs text-arc-muted mt-1">entrar</div>
              </motion.button>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.1 }} className="arc-card p-8 md:p-10">
          <h2 className="font-fredoka text-3xl font-bold text-arc-text mb-1">Bem-vindo(a) de volta!</h2>
          <p className="text-arc-muted mb-6">Entre para continuar sua jornada financeira.</p>
          <form onSubmit={doLogin} className="space-y-4" noValidate>
            <div>
              <label className="block text-sm font-semibold text-arc-text mb-2">E-mail ou login</label>
              <input data-testid="login-email-input" type="text" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} className="arc-input" placeholder="seu@email.edu ou @primeironome" required />
            </div>
            <div>
              <label className="block text-sm font-semibold text-arc-text mb-2">Senha</label>
              <input data-testid="login-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="arc-input" placeholder="••••••••" required />
            </div>
            {error && <div className="text-arc-accent font-semibold text-sm bg-pink-50 p-3 rounded-2xl">{error}</div>}
            <button data-testid="login-submit-btn" type="submit" disabled={loading} className="arc-btn arc-btn-primary w-full disabled:opacity-60">
              {loading ? "Entrando..." : "Entrar na plataforma →"}
            </button>
          </form>
          <div className="mt-6 p-4 bg-arc rounded-2xl text-xs text-arc-muted">
            <strong className="text-arc-text">💡 Dica:</strong> Use os atalhos à esquerda para entrar rapidamente como Aluno, Professor ou Admin.
          </div>
        </motion.div>
      </div>
    </div>
  );
}
