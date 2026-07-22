import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Shell from "../components/Shell";
import { useAuth, API } from "../auth";

const TEACHER_NAV = [
  { key: "home", label: "Turmas", to: "/professor" },
  { key: "create", label: "Criar Desafio", to: "/professor/criar" },
  { key: "approvals", label: "Aprovações", to: "/professor/aprovacoes" },
  { key: "vouchers", label: "🎟️ Vouchers", to: "/professor/vouchers" },
  { key: "attendance", label: "✅ Presença", to: "/professor/presenca" },
];

const ADMIN_NAV = [
  { key: "home", label: "Visão Geral", to: "/admin" },
  { key: "users", label: "Usuários", to: "/admin/usuarios" },
  { key: "classes", label: "Turmas", to: "/admin/turmas" },
  { key: "attendance", label: "✅ Presença", to: "/admin/presenca" },
  { key: "vouchers", label: "🎟️ Vouchers", to: "/admin/vouchers" },
  { key: "store", label: "Loja", to: "/admin/loja" },
  { key: "config", label: "Configurações", to: "/admin/config" },
];

const today = () => new Date().toISOString().slice(0, 10);

export default function Attendance() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const NAV = isAdmin ? ADMIN_NAV : TEACHER_NAV;
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState("");
  const [date, setDate] = useState(today());
  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState({}); // student_id -> true/false/null
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API}/teacher/classes`).then((r) => {
      setClasses(r.data);
      if (r.data.length > 0 && !classId) setClassId(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!classId || !date) return;
    (async () => {
      const { data } = await axios.get(`${API}/attendance/class/${classId}?date=${date}`);
      setStudents(data.students);
      const map = {};
      data.students.forEach((s) => {
        map[s.id] = s.attendance?.marked ? s.attendance.present : null;
      });
      setAttendance(map);
    })();
  }, [classId, date]);

  const setStatus = (sid, present) => setAttendance((a) => ({ ...a, [sid]: present }));

  const markAll = (present) => {
    const map = {};
    students.forEach((s) => (map[s.id] = present));
    setAttendance(map);
  };

  const save = async () => {
    setLoading(true); setMsg(null);
    const present_ids = Object.entries(attendance).filter(([_, v]) => v === true).map(([k]) => k);
    const absent_ids = Object.entries(attendance).filter(([_, v]) => v === false).map(([k]) => k);
    if (present_ids.length + absent_ids.length === 0) {
      setMsg({ type: "error", text: "Marque pelo menos 1 aluno" });
      setLoading(false); return;
    }
    try {
      const { data } = await axios.post(`${API}/attendance/mark`, {
        class_id: classId, date, present_ids, absent_ids,
      });
      setMsg({ type: "success", text: `✅ Presença registrada — ${data.count} aluno(s) atualizado(s)` });
    } catch (err) {
      setMsg({ type: "error", text: err?.response?.data?.detail || "Erro ao salvar" });
    }
    setLoading(false);
    setTimeout(() => setMsg(null), 4000);
  };

  const presentCount = Object.values(attendance).filter((v) => v === true).length;
  const absentCount = Object.values(attendance).filter((v) => v === false).length;
  const unmarkedCount = students.length - presentCount - absentCount;

  return (
    <Shell nav={NAV} title="Presença">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-fredoka font-bold text-2xl text-arc-text">✅ Chamada de presença</h2>
        <div className="text-sm text-arc-muted">
          <strong className="text-arc-success">{presentCount}</strong> presentes ·
          <strong className="text-arc-accent ml-1">{absentCount}</strong> ausentes ·
          <strong className="text-arc-text ml-1">{unmarkedCount}</strong> não marcados
        </div>
      </div>

      {msg && (
        <div className={`mb-4 p-4 rounded-2xl font-semibold ${msg.type === "success" ? "bg-arc-success text-arc-text" : "bg-pink-100 text-arc-accent"}`} data-testid="attendance-msg">
          {msg.text}
        </div>
      )}

      <div className="grid md:grid-cols-4 gap-3 mb-6">
        <div>
          <label className="text-xs font-semibold text-arc-muted uppercase">Turma</label>
          <select data-testid="att-class" className="arc-input mt-1" value={classId} onChange={(e) => setClassId(e.target.value)}>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-arc-muted uppercase">Data</label>
          <input data-testid="att-date" type="date" className="arc-input mt-1" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="flex items-end gap-2 md:col-span-2">
          <button data-testid="mark-all-present" onClick={() => markAll(true)} className="arc-btn arc-btn-success text-sm py-2 flex-1">Todos presentes</button>
          <button onClick={() => markAll(false)} className="arc-btn arc-btn-outline text-sm py-2 flex-1">Todos ausentes</button>
        </div>
      </div>

      <div className="arc-card p-4 md:p-6">
        {students.length === 0 && <div className="text-center text-arc-muted py-6">Nenhum aluno nesta turma.</div>}
        <div className="space-y-2" data-testid="attendance-list">
          {students.map((s) => {
            const st = attendance[s.id];
            return (
              <motion.div key={s.id} className="flex items-center gap-4 p-3 rounded-2xl bg-arc" whileHover={{ x: 2 }}>
                <img src={s.avatar} alt="" className="w-11 h-11 rounded-full bg-white" />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-arc-text truncate">{s.name}</div>
                  <div className="text-xs text-arc-muted">{s.ra ? `RA ${s.ra}` : s.email}</div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setStatus(s.id, true)}
                    data-testid={`present-${s.id}`}
                    className="px-4 py-2 rounded-full text-sm font-bold transition-all"
                    style={{
                      background: st === true ? "#06D6A0" : "transparent",
                      color: st === true ? "#073B4C" : "var(--arc-muted)",
                      border: st === true ? "2px solid #06D6A0" : "2px solid #E2E8F0",
                    }}
                  >✓ Presente</button>
                  <button
                    onClick={() => setStatus(s.id, false)}
                    data-testid={`absent-${s.id}`}
                    className="px-4 py-2 rounded-full text-sm font-bold transition-all"
                    style={{
                      background: st === false ? "#FF006E" : "transparent",
                      color: st === false ? "#fff" : "var(--arc-muted)",
                      border: st === false ? "2px solid #FF006E" : "2px solid #E2E8F0",
                    }}
                  >✕ Ausente</button>
                </div>
              </motion.div>
            );
          })}
        </div>
        <button data-testid="save-attendance" onClick={save} disabled={loading || students.length === 0} className="arc-btn arc-btn-primary w-full mt-6 disabled:opacity-50">
          {loading ? "Salvando..." : "💾 Salvar presença"}
        </button>
      </div>

      <div className="mt-6 arc-card p-5 bg-arc">
        <div className="text-sm text-arc-text">
          💡 <strong>Mesada condicional:</strong> nas Configurações, ative a opção <em>"Mesada apenas para alunos presentes"</em>.
          Quando ativada, ao clicar em <em>"Distribuir mesada"</em> na Visão Geral, apenas os alunos marcados como <strong>presentes hoje</strong> receberão a mesada.
        </div>
      </div>
    </Shell>
  );
}
