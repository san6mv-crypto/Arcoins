import React, { useEffect, useState } from "react";
import axios from "axios";
import Shell from "../components/Shell";
import { API } from "../auth";
import { ArcSymbol } from "../Mascot";

const NAV = [
  { key: "home", label: "Visão Geral", to: "/admin" },
  { key: "users", label: "Usuários", to: "/admin/usuarios" },
  { key: "store", label: "Loja", to: "/admin/loja" },
  { key: "config", label: "Configurações", to: "/admin/config" },
];

export function AdminHome() {
  const [stats, setStats] = useState(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { axios.get(`${API}/admin/stats`).then((r) => setStats(r.data)); }, []);
  const runAllowance = async () => {
    const r = await axios.post(`${API}/admin/run-allowance`);
    setMsg(`💰 Mesada distribuída para ${r.data.distributed_to} aluno(s) — ₡ ${r.data.amount} cada.`);
    axios.get(`${API}/admin/stats`).then((x) => setStats(x.data));
    setTimeout(() => setMsg(""), 4000);
  };
  if (!stats) return <Shell nav={NAV} title="Administração"><div>Carregando...</div></Shell>;
  return (
    <Shell nav={NAV} title="Administração">
      <div className="arc-card p-6 md:p-8 mb-6" style={{ background: "linear-gradient(135deg,#FF006E 0%,#D9005D 100%)", color: "#fff" }}>
        <h2 className="font-fredoka text-3xl font-bold">Painel Administrativo 🏫</h2>
        <p className="mt-1 opacity-90">Visão geral da plataforma Arcoins na sua escola.</p>
      </div>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-success font-semibold text-arc-text">{msg}</div>}
      <div className="grid md:grid-cols-4 gap-5 mb-8">
        <S label="Alunos" value={stats.students} icon="🎒" color="#00B4D8" />
        <S label="Professores" value={stats.teachers} icon="📚" color="#06D6A0" />
        <S label="Desafios ativos" value={stats.active_challenges} icon="🎯" color="#FFBE0B" />
        <S label="Itens na loja" value={stats.store_items} icon="🛍️" color="#FF006E" />
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="arc-card p-6 md:col-span-2">
          <h3 className="font-fredoka font-bold text-lg text-arc-text mb-4">Economia da escola</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-arc">
              <div className="text-xs font-bold text-arc-muted uppercase">Arc em circulação</div>
              <div className="font-fredoka font-bold text-3xl text-arc-primary mt-2"><ArcSymbol /> {stats.arc_in_circulation.toFixed(2)}</div>
            </div>
            <div className="p-5 rounded-2xl bg-arc">
              <div className="text-xs font-bold text-arc-muted uppercase">Arc em poupanças</div>
              <div className="font-fredoka font-bold text-3xl text-arc-success mt-2"><ArcSymbol /> {stats.arc_in_savings.toFixed(2)}</div>
            </div>
          </div>
          <div className="mt-4 text-sm text-arc-muted">Compras totais na loja: <strong className="text-arc-text">{stats.total_purchases}</strong></div>
        </div>
        <div className="arc-card p-6">
          <h3 className="font-fredoka font-bold text-lg text-arc-text mb-3">Ações rápidas</h3>
          <button data-testid="run-allowance" onClick={runAllowance} className="arc-btn arc-btn-secondary w-full mb-3">💸 Distribuir mesada diária</button>
          <a href="/admin/config" className="arc-btn arc-btn-outline w-full text-center block">⚙️ Configurações</a>
          <div className="mt-4 text-xs text-arc-muted">A mesada não é duplicada se já houver sido distribuída hoje.</div>
        </div>
      </div>
    </Shell>
  );
}

function S({ label, value, icon, color }) {
  return (
    <div className="arc-card p-5" style={{ borderTop: `5px solid ${color}` }}>
      <div className="flex items-center justify-between">
        <div className="text-3xl">{icon}</div>
        <div className="font-fredoka font-bold text-3xl text-arc-text">{value}</div>
      </div>
      <div className="text-sm font-semibold text-arc-muted mt-2 uppercase tracking-wide">{label}</div>
    </div>
  );
}

export function AdminUsers() {
  const [users, setUsers] = useState([]);
  useEffect(() => { axios.get(`${API}/admin/users`).then((r) => setUsers(r.data)); }, []);
  return (
    <Shell nav={NAV} title="Usuários">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">👥 Usuários da plataforma</h2>
      <div className="arc-card p-4 md:p-6">
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="flex items-center gap-4 p-3 rounded-2xl hover:bg-arc">
              <img src={u.avatar || "https://api.dicebear.com/7.x/avataaars/svg?seed=U"} alt="" className="w-11 h-11 rounded-full bg-arc" />
              <div className="flex-1">
                <div className="font-semibold text-arc-text">{u.name}</div>
                <div className="text-xs text-arc-muted">{u.email}</div>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold uppercase" style={{ background: u.role === "admin" ? "#FF006E" : u.role === "teacher" ? "#06D6A0" : "#00B4D8", color: "#fff" }}>
                {u.role === "student" ? "aluno" : u.role === "teacher" ? "professor" : "admin"}
              </span>
              {u.role === "student" && <div className="font-fredoka font-bold text-arc-primary w-24 text-right"><ArcSymbol /> {u.balance?.toFixed(2)}</div>}
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

export function AdminStore() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", price: 10, stock: 20, image: "" });
  const load = async () => { const r = await axios.get(`${API}/admin/store`); setItems(r.data); };
  useEffect(() => { load(); }, []);
  const add = async (e) => {
    e.preventDefault();
    await axios.post(`${API}/admin/store`, { ...form, price: parseFloat(form.price), stock: parseInt(form.stock) });
    setForm({ name: "", description: "", price: 10, stock: 20, image: "" }); load();
  };
  const del = async (id) => { await axios.delete(`${API}/admin/store/${id}`); load(); };
  return (
    <Shell nav={NAV} title="Gerenciar Loja">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">🛍️ Gerenciamento da Loja</h2>
      <div className="grid md:grid-cols-3 gap-6">
        <form onSubmit={add} className="arc-card p-6 md:col-span-1 space-y-3 h-fit">
          <h3 className="font-fredoka font-bold text-lg text-arc-text">Adicionar item</h3>
          <input required placeholder="Nome" className="arc-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <textarea required placeholder="Descrição" rows={2} className="arc-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <input required type="number" placeholder="Preço em Arc" className="arc-input" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
          <input required type="number" placeholder="Estoque" className="arc-input" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
          <input placeholder="URL da imagem (opcional)" className="arc-input" value={form.image} onChange={(e) => setForm({ ...form, image: e.target.value })} />
          <button className="arc-btn arc-btn-primary w-full">Adicionar</button>
        </form>
        <div className="md:col-span-2 grid md:grid-cols-2 gap-4">
          {items.filter((i) => i.active).map((it) => (
            <div key={it.id} className="arc-card p-4 flex gap-4">
              <div className="w-20 h-20 rounded-2xl bg-arc flex-shrink-0" style={{ backgroundImage: `url(${it.image})`, backgroundSize: "cover", backgroundPosition: "center" }} />
              <div className="flex-1">
                <div className="font-bold text-arc-text">{it.name}</div>
                <div className="text-xs text-arc-muted line-clamp-2">{it.description}</div>
                <div className="flex items-center justify-between mt-2">
                  <div className="font-fredoka font-bold text-arc-secondary"><ArcSymbol /> {it.price}</div>
                  <div className="text-xs text-arc-muted">estoque: {it.stock}</div>
                </div>
              </div>
              <button onClick={() => del(it.id)} className="text-arc-accent font-bold text-xs">Remover</button>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

export function AdminConfig() {
  const [cfg, setCfg] = useState(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { axios.get(`${API}/admin/config`).then((r) => setCfg(r.data)); }, []);
  const save = async () => {
    await axios.post(`${API}/admin/config`, { daily_allowance: parseFloat(cfg.daily_allowance), savings_rate: parseFloat(cfg.savings_rate) });
    setMsg("✅ Configurações salvas!"); setTimeout(() => setMsg(""), 3000);
  };
  if (!cfg) return <Shell nav={NAV} title="Configurações">Carregando...</Shell>;
  return (
    <Shell nav={NAV} title="Configurações">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">⚙️ Configurações da plataforma</h2>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-success font-semibold text-arc-text">{msg}</div>}
      <div className="arc-card p-6 md:p-8 max-w-xl space-y-5">
        <div>
          <label className="text-sm font-semibold text-arc-text block mb-2">Mesada diária (em <ArcSymbol /> Arc)</label>
          <input data-testid="cfg-allowance" type="number" step="0.5" className="arc-input" value={cfg.daily_allowance} onChange={(e) => setCfg({ ...cfg, daily_allowance: e.target.value })} />
          <div className="text-xs text-arc-muted mt-1">Valor distribuído a cada aluno por dia letivo.</div>
        </div>
        <div>
          <label className="text-sm font-semibold text-arc-text block mb-2">Taxa de rendimento da poupança (diária, 0.02 = 2%)</label>
          <input data-testid="cfg-savings" type="number" step="0.001" className="arc-input" value={cfg.savings_rate} onChange={(e) => setCfg({ ...cfg, savings_rate: e.target.value })} />
        </div>
        <button data-testid="save-cfg" onClick={save} className="arc-btn arc-btn-primary w-full">Salvar</button>
      </div>
    </Shell>
  );
}
