import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Shell from "../components/Shell";
import { useAuth, API } from "../auth";
import { ArcSymbol } from "../Mascot";

const NAV = [
  { key: "home", label: "Turmas", to: "/professor" },
  { key: "create", label: "Criar Desafio", to: "/professor/criar" },
  { key: "approvals", label: "Aprovações", to: "/professor/aprovacoes" },
  { key: "vouchers", label: "🎟️ Vouchers", to: "/professor/vouchers" },
];

export function TeacherHome() {
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);
  useEffect(() => {
    axios.get(`${API}/teacher/classes`).then((r) => setClasses(r.data));
    axios.get(`${API}/teacher/students`).then((r) => setStudents(r.data));
  }, []);
  return (
    <Shell nav={NAV} title="Área do Professor">
      <div className="arc-card p-6 md:p-8 mb-6" style={{ background: "linear-gradient(135deg,#06D6A0 0%,#05B88A 100%)", color: "#073B4C" }}>
        <h2 className="font-fredoka text-3xl font-bold">Olá, {user?.name}! 📚</h2>
        <p className="mt-1 text-arc-text/80">Gerencie suas turmas, crie desafios e acompanhe o progresso financeiro dos alunos.</p>
      </div>
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <Stat label="Turmas" value={classes.length} color="#00B4D8" icon="🏫" />
        <Stat label="Alunos" value={students.length} color="#FFBE0B" icon="🎒" />
        <Stat label="Arc em circulação" value={`₡ ${students.reduce((a, s) => a + (s.balance || 0), 0).toFixed(0)}`} color="#FF006E" icon="💰" />
      </div>
      <h3 className="font-fredoka font-bold text-xl text-arc-text mb-4">Suas turmas</h3>
      <div className="grid md:grid-cols-2 gap-5 mb-8">
        {classes.map((c) => (
          <motion.div key={c.id} className="arc-card p-6" whileHover={{ y: -4 }}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-fredoka font-bold text-xl text-arc-text">{c.name}</div>
                <div className="text-sm text-arc-muted">{c.student_count} alunos</div>
              </div>
              <div className="text-4xl">📘</div>
            </div>
          </motion.div>
        ))}
      </div>
      <h3 className="font-fredoka font-bold text-xl text-arc-text mb-4">Alunos</h3>
      <div className="arc-card p-4 md:p-6">
        <div className="space-y-2" data-testid="students-list">
          {students.map((s) => (
            <div key={s.id} className="flex items-center gap-4 p-3 rounded-2xl hover:bg-arc">
              <img src={s.avatar} alt="" className="w-11 h-11 rounded-full bg-arc" />
              <div className="flex-1">
                <div className="font-semibold text-arc-text">{s.name}</div>
                <div className="text-xs text-arc-muted">{s.email}</div>
              </div>
              <div className="text-right">
                <div className="font-fredoka font-bold text-arc-primary"><ArcSymbol /> {s.balance?.toFixed(2)}</div>
                <div className="text-xs text-arc-muted">poupança: {s.savings?.toFixed(2)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

function Stat({ label, value, color, icon }) {
  return (
    <div className="arc-card p-6" style={{ borderLeft: `6px solid ${color}` }}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-arc-muted font-semibold uppercase tracking-wide">{label}</div>
          <div className="font-fredoka font-bold text-3xl text-arc-text mt-1">{value}</div>
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

export function TeacherCreate() {
  const [classes, setClasses] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", reward: 10, class_id: "" });
  const [msg, setMsg] = useState("");
  useEffect(() => { axios.get(`${API}/teacher/classes`).then((r) => setClasses(r.data)); }, []);
  const submit = async (e) => {
    e.preventDefault();
    try { await axios.post(`${API}/teacher/challenges`, { ...form, reward: parseFloat(form.reward), class_id: form.class_id || null }); setMsg("✅ Desafio criado!"); setForm({ title: "", description: "", reward: 10, class_id: "" }); }
    catch (e) { setMsg("Erro ao criar."); }
    setTimeout(() => setMsg(""), 3000);
  };
  return (
    <Shell nav={NAV} title="Criar Desafio">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">✨ Criar novo desafio</h2>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-success font-semibold text-arc-text">{msg}</div>}
      <form onSubmit={submit} className="arc-card p-6 md:p-8 max-w-2xl space-y-4">
        <div>
          <label className="text-sm font-semibold text-arc-text block mb-2">Título</label>
          <input data-testid="ch-title" required className="arc-input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="text-sm font-semibold text-arc-text block mb-2">Descrição</label>
          <textarea data-testid="ch-desc" required rows={3} className="arc-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-semibold text-arc-text block mb-2">Recompensa (<ArcSymbol />)</label>
            <input data-testid="ch-reward" type="number" step="0.5" min="0" className="arc-input" value={form.reward} onChange={(e) => setForm({ ...form, reward: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-semibold text-arc-text block mb-2">Turma</label>
            <select className="arc-input" value={form.class_id} onChange={(e) => setForm({ ...form, class_id: e.target.value })}>
              <option value="">Toda a escola</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>
        <button data-testid="create-ch-btn" className="arc-btn arc-btn-primary w-full">Criar desafio 🎯</button>
      </form>
    </Shell>
  );
}

export function TeacherApprovals() {
  const [subs, setSubs] = useState([]);
  const load = async () => { const r = await axios.get(`${API}/teacher/submissions`); setSubs(r.data); };
  useEffect(() => { load(); }, []);
  const review = async (id, approve) => { await axios.post(`${API}/teacher/submissions/${id}/review?approve=${approve}`); load(); };
  return (
    <Shell nav={NAV} title="Aprovações">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">✅ Aprovações pendentes</h2>
      {subs.length === 0 && <div className="arc-card p-8 text-center text-arc-muted">🎉 Nenhuma submissão pendente!</div>}
      <div className="space-y-3">
        {subs.map((s) => (
          <div key={s.id} className="arc-card p-5 flex items-center justify-between gap-4">
            <div>
              <div className="font-fredoka font-bold text-lg text-arc-text">{s.challenge_title}</div>
              <div className="text-sm text-arc-muted">Aluno: <strong>{s.student_name}</strong> · Recompensa: <span className="text-arc-secondary font-bold"><ArcSymbol /> {s.reward}</span></div>
            </div>
            <div className="flex gap-2">
              <button data-testid={`approve-${s.id}`} onClick={() => review(s.id, true)} className="arc-btn arc-btn-success text-sm py-2">Aprovar</button>
              <button onClick={() => review(s.id, false)} className="arc-btn arc-btn-outline text-sm py-2">Rejeitar</button>
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
