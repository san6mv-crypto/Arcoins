import React, { useEffect, useState } from "react";
import axios from "axios";
import Shell from "../components/Shell";
import { useAuth, API } from "../auth";
import { ArcSymbol } from "../Mascot";

const TEACHER_NAV = [
  { key: "home", label: "Turmas", to: "/professor" },
  { key: "create", label: "Criar Desafio", to: "/professor/criar" },
  { key: "approvals", label: "Aprovações", to: "/professor/aprovacoes" },
  { key: "vouchers", label: "🎟️ Vouchers", to: "/professor/vouchers" },
];

const ADMIN_NAV = [
  { key: "home", label: "Visão Geral", to: "/admin" },
  { key: "users", label: "Usuários", to: "/admin/usuarios" },
  { key: "classes", label: "Turmas", to: "/admin/turmas" },
  { key: "vouchers", label: "🎟️ Vouchers", to: "/admin/vouchers" },
  { key: "store", label: "Loja", to: "/admin/loja" },
  { key: "config", label: "Configurações", to: "/admin/config" },
];

export default function Vouchers() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const NAV = isAdmin ? ADMIN_NAV : TEACHER_NAV;
  const [vouchers, setVouchers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [form, setForm] = useState({ value: 10, description: "", code: "", class_id: "" });
  const [msg, setMsg] = useState(null);
  const [copied, setCopied] = useState("");

  const load = async () => {
    const [v, c] = await Promise.all([
      axios.get(`${API}/vouchers`),
      axios.get(`${API}/teacher/classes`),
    ]);
    setVouchers(v.data); setClasses(c.data);
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setMsg(null);
    try {
      const body = {
        value: parseFloat(form.value),
        description: form.description.trim(),
        code: form.code.trim() || null,
        class_id: form.class_id || null,
      };
      const { data } = await axios.post(`${API}/vouchers`, body);
      setMsg({ type: "success", text: `🎟️ Voucher criado! Código: ${data.code}` });
      setForm({ value: 10, description: "", code: "", class_id: "" });
      load();
    } catch (err) {
      setMsg({ type: "error", text: err?.response?.data?.detail || "Erro ao criar voucher" });
    }
    setTimeout(() => setMsg(null), 4000);
  };

  const remove = async (id) => {
    if (!window.confirm("Remover este voucher? Esta ação não pode ser desfeita.")) return;
    try { await axios.delete(`${API}/vouchers/${id}`); load(); }
    catch (err) { alert(err?.response?.data?.detail || "Erro"); }
  };

  const copy = (code) => {
    navigator.clipboard?.writeText(code);
    setCopied(code);
    setTimeout(() => setCopied(""), 1500);
  };

  const active = vouchers.filter((v) => !v.redeemed_by);
  const used = vouchers.filter((v) => v.redeemed_by);

  return (
    <Shell nav={NAV} title="Vouchers">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-fredoka font-bold text-2xl text-arc-text">🎟️ Vouchers de bonificação</h2>
        <div className="text-sm text-arc-muted">
          <strong className="text-arc-text">{active.length}</strong> ativos · <strong className="text-arc-text">{used.length}</strong> resgatados
        </div>
      </div>

      {msg && (
        <div className={`mb-4 p-4 rounded-2xl font-semibold ${msg.type === "success" ? "bg-arc-success text-arc-text" : "bg-pink-100 text-arc-accent"}`} data-testid="voucher-msg">
          {msg.text}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <form onSubmit={submit} className="arc-card p-6 space-y-4 h-fit" data-testid="voucher-form">
          <h3 className="font-fredoka font-bold text-lg text-arc-text">➕ Criar voucher</h3>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">Valor (em ₡ Arc)</label>
            <input required type="number" step="1" min="1" data-testid="voucher-value" className="arc-input mt-1" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">Descrição (opcional)</label>
            <input data-testid="voucher-desc" className="arc-input mt-1" placeholder="Ex: Prêmio da olimpíada" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">Código (deixe vazio para gerar)</label>
            <input data-testid="voucher-code-input" maxLength={20} className="arc-input mt-1 uppercase font-mono tracking-wider" placeholder="EX: EXTRA2026" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
          </div>
          {classes.length > 0 && (
            <div>
              <label className="text-xs font-semibold text-arc-muted uppercase">Restringir à turma (opcional)</label>
              <select data-testid="voucher-class" className="arc-input mt-1" value={form.class_id} onChange={(e) => setForm({ ...form, class_id: e.target.value })}>
                <option value="">Qualquer aluno</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          )}
          <button type="submit" data-testid="voucher-create-btn" className="arc-btn arc-btn-primary w-full">Gerar voucher 🎟️</button>
          <div className="text-xs text-arc-muted bg-arc p-3 rounded-2xl">
            💡 Voucher é de <strong>uso único</strong>. O primeiro aluno que digitar o código resgata.
          </div>
        </form>

        <div className="lg:col-span-2 space-y-6">
          <div>
            <h3 className="font-fredoka font-bold text-lg text-arc-text mb-3">🟢 Ativos ({active.length})</h3>
            {active.length === 0 && <div className="arc-card p-6 text-center text-arc-muted text-sm">Nenhum voucher ativo.</div>}
            <div className="grid sm:grid-cols-2 gap-3">
              {active.map((v) => (
                <div key={v.id} className="arc-card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <button onClick={() => copy(v.code)} data-testid={`copy-${v.code}`} className="font-mono font-bold text-lg text-arc-primary tracking-wider hover:underline">
                      {v.code} {copied === v.code && <span className="text-xs text-arc-success ml-1">✓ copiado</span>}
                    </button>
                    <div className="font-fredoka font-bold text-arc-secondary"><ArcSymbol /> {v.value}</div>
                  </div>
                  {v.description && <div className="text-xs text-arc-muted mb-2">{v.description}</div>}
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-arc-muted">por {v.created_by_name}</div>
                    <button onClick={() => remove(v.id)} className="text-xs text-arc-accent font-bold hover:underline">Remover</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {used.length > 0 && (
            <div>
              <h3 className="font-fredoka font-bold text-lg text-arc-text mb-3">⚪ Resgatados ({used.length})</h3>
              <div className="space-y-2">
                {used.map((v) => (
                  <div key={v.id} className="arc-card p-3 flex items-center justify-between text-sm">
                    <div>
                      <code className="font-mono font-bold text-arc-muted">{v.code}</code>
                      <span className="text-arc-muted ml-2">→ <strong className="text-arc-text">{v.redeemed_by_name}</strong></span>
                    </div>
                    <div className="font-fredoka font-bold text-arc-success"><ArcSymbol /> {v.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
