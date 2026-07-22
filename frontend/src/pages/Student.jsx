import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Confetti from "react-confetti";
import Shell from "../components/Shell";
import { useAuth, API } from "../auth";
import { ArcoinMascot, ArcSymbol } from "../Mascot";
import VoucherWidget from "../components/VoucherWidget";

const NAV = [
  { key: "home", label: "Início", to: "/aluno" },
  { key: "extrato", label: "Extrato", to: "/aluno/extrato" },
  { key: "desafios", label: "Desafios", to: "/aluno/desafios" },
  { key: "loja", label: "Loja", to: "/aluno/loja" },
  { key: "poupanca", label: "Poupança", to: "/aluno/poupanca" },
  { key: "transferir", label: "🔁 Transferir", to: "/aluno/transferir" },
];

function Balance({ balance, savings }) {
  return (
    <div className="arc-card p-6 md:p-8" style={{ background: "linear-gradient(135deg,#00B4D8 0%,#0096C7 100%)", color: "#fff" }}>
      <div className="flex items-start justify-between">
        <div>
          <div className="font-nunito text-sm opacity-90 font-semibold uppercase tracking-wide">Seu saldo</div>
          <motion.div className="flex items-baseline gap-2 mt-2" animate={{ scale: [1, 1.02, 1] }} transition={{ repeat: Infinity, duration: 2.8 }}>
            <span className="font-fredoka font-bold text-5xl md:text-6xl" style={{ color: "#FFBE0B" }}>₡</span>
            <span className="font-fredoka font-bold text-5xl md:text-6xl">{balance?.toFixed(2)}</span>
          </motion.div>
          <div className="mt-3 text-sm opacity-90">Poupança: <strong><ArcSymbol className="text-yellow-300" /> {savings?.toFixed(2)}</strong></div>
        </div>
        <div className="animate-float"><ArcoinMascot size={90} /></div>
      </div>
    </div>
  );
}

export function StudentHome() {
  const { user, refresh } = useAuth();
  const [challenges, setChallenges] = useState([]);
  const [txns, setTxns] = useState([]);

  useEffect(() => {
    (async () => {
      const [c, t] = await Promise.all([
        axios.get(`${API}/student/challenges`),
        axios.get(`${API}/student/transactions`),
      ]);
      setChallenges(c.data.slice(0, 3));
      setTxns(t.data.slice(0, 5));
    })();
  }, []);

  return (
    <Shell nav={NAV} title="Área do Aluno">
      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2"><Balance balance={user?.balance || 0} savings={user?.savings || 0} /></div>
        <div className="arc-card p-6">
          <h3 className="font-fredoka font-bold text-lg text-arc-text">Olá, {user?.name?.split(" ")[0]}! 👋</h3>
          <p className="text-sm text-arc-muted mt-2">Complete desafios para ganhar mais <ArcSymbol /> Arc e compre itens legais na loja!</p>
          <button onClick={refresh} data-testid="refresh-btn" className="arc-btn arc-btn-secondary mt-4 text-sm py-2">Atualizar saldo</button>
        </div>
      </div>
      <div className="mt-6">
        <VoucherWidget />
      </div>

      <div className="mt-8 grid md:grid-cols-2 gap-6">
        <div className="arc-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-fredoka font-bold text-xl text-arc-text">🎯 Desafios ativos</h3>
            <a href="/aluno/desafios" className="text-sm text-arc-primary font-semibold">ver todos →</a>
          </div>
          {challenges.length === 0 && <div className="text-arc-muted">Nenhum desafio disponível.</div>}
          <div className="space-y-3">
            {challenges.map((c) => (
              <div key={c.id} className="p-4 rounded-2xl bg-arc flex items-center justify-between">
                <div>
                  <div className="font-semibold text-arc-text">{c.title}</div>
                  <div className="text-xs text-arc-muted line-clamp-1">{c.description}</div>
                </div>
                <div className="font-fredoka font-bold text-arc-success whitespace-nowrap"><ArcSymbol /> {c.reward}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="arc-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-fredoka font-bold text-xl text-arc-text">📜 Últimas transações</h3>
            <a href="/aluno/extrato" className="text-sm text-arc-primary font-semibold">extrato →</a>
          </div>
          <div className="space-y-2">
            {txns.map((t) => (
              <div key={t.id} className="flex items-center justify-between py-2 border-b last:border-0" style={{ borderColor: "var(--arc-border)" }}>
                <div>
                  <div className="text-sm font-semibold text-arc-text">{t.description}</div>
                  <div className="text-xs text-arc-muted">{new Date(t.created_at).toLocaleDateString("pt-BR")}</div>
                </div>
                <div className={`font-fredoka font-bold ${t.amount >= 0 ? "text-arc-success" : "text-arc-accent"}`}>
                  {t.amount >= 0 ? "+" : ""}{t.amount.toFixed(2)} <ArcSymbol />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}

export function StudentExtrato() {
  const [txns, setTxns] = useState([]);
  useEffect(() => { axios.get(`${API}/student/transactions`).then((r) => setTxns(r.data)); }, []);
  return (
    <Shell nav={NAV} title="Extrato">
      <div className="arc-card p-6 md:p-8">
        <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">📊 Seu extrato completo</h2>
        <div className="space-y-2" data-testid="extrato-list">
          {txns.map((t) => (
            <div key={t.id} className="flex items-center justify-between p-4 rounded-2xl bg-arc">
              <div>
                <div className="font-semibold text-arc-text">{t.description}</div>
                <div className="text-xs text-arc-muted capitalize">{t.type.replace("_", " ")} · {new Date(t.created_at).toLocaleString("pt-BR")}</div>
              </div>
              <div className={`font-fredoka font-bold text-lg ${t.amount >= 0 ? "text-arc-success" : "text-arc-accent"}`}>
                {t.amount >= 0 ? "+" : ""}{t.amount.toFixed(2)} <ArcSymbol />
              </div>
            </div>
          ))}
          {txns.length === 0 && <div className="text-center text-arc-muted py-8">Nenhuma transação ainda.</div>}
        </div>
      </div>
    </Shell>
  );
}

export function StudentChallenges() {
  const { refresh } = useAuth();
  const [list, setList] = useState([]);
  const [msg, setMsg] = useState("");
  const load = async () => { const r = await axios.get(`${API}/student/challenges`); setList(r.data); };
  useEffect(() => { load(); }, []);
  const submit = async (id) => {
    try { await axios.post(`${API}/student/challenges/${id}/submit`); setMsg("Submissão enviada! Aguarde aprovação do professor."); load(); await refresh(); }
    catch (e) { setMsg(e?.response?.data?.detail || "Erro ao enviar."); }
    setTimeout(() => setMsg(""), 3000);
  };
  return (
    <Shell nav={NAV} title="Desafios">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-4">🎯 Desafios disponíveis</h2>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-success text-arc-text font-semibold">{msg}</div>}
      <div className="grid md:grid-cols-2 gap-5">
        {list.map((c) => (
          <motion.div key={c.id} className="arc-card p-6" whileHover={{ y: -4 }}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="font-fredoka font-bold text-lg text-arc-text">{c.title}</div>
                <p className="text-sm text-arc-muted mt-1">{c.description}</p>
              </div>
              <div className="text-center px-3 py-2 rounded-2xl bg-arc">
                <div className="font-fredoka font-bold text-xl text-arc-secondary"><ArcSymbol />{c.reward}</div>
                <div className="text-xs text-arc-muted">recompensa</div>
              </div>
            </div>
            <div className="mt-4">
              {c.submission_status === "approved" && <div className="text-arc-success font-bold">✅ Concluído</div>}
              {c.submission_status === "pending" && <div className="text-arc-secondary font-bold">⏳ Aguardando aprovação</div>}
              {c.submission_status === "rejected" && <button onClick={() => submit(c.id)} className="arc-btn arc-btn-accent">Tentar novamente</button>}
              {!c.submission_status && <button data-testid={`submit-challenge-${c.id}`} onClick={() => submit(c.id)} className="arc-btn arc-btn-primary w-full">Marcar como concluído</button>}
            </div>
          </motion.div>
        ))}
      </div>
    </Shell>
  );
}

export function StudentStore() {
  const { user, refresh } = useAuth();
  const [items, setItems] = useState([]);
  const [confetti, setConfetti] = useState(false);
  const [msg, setMsg] = useState("");
  const load = async () => { const r = await axios.get(`${API}/student/store`); setItems(r.data); };
  useEffect(() => { load(); }, []);
  const buy = async (id) => {
    try { await axios.post(`${API}/student/store/buy`, { item_id: id }); setConfetti(true); setMsg("🎉 Compra realizada com sucesso!"); setTimeout(() => setConfetti(false), 3500); await refresh(); load(); }
    catch (e) { setMsg(e?.response?.data?.detail || "Erro na compra"); }
    setTimeout(() => setMsg(""), 3000);
  };
  return (
    <Shell nav={NAV} title="Loja Escolar">
      {confetti && <Confetti numberOfPieces={200} recycle={false} />}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-fredoka font-bold text-2xl text-arc-text">🛍️ Loja Escolar</h2>
        <div className="font-fredoka text-lg">Seu saldo: <span className="font-bold text-arc-primary"><ArcSymbol /> {user?.balance?.toFixed(2)}</span></div>
      </div>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-secondary font-semibold text-arc-text">{msg}</div>}
      <div className="grid md:grid-cols-3 gap-6">
        {items.map((it) => (
          <motion.div key={it.id} className="arc-card overflow-hidden" whileHover={{ y: -4 }}>
            <div className="h-40 bg-arc" style={{ backgroundImage: `url(${it.image})`, backgroundSize: "cover", backgroundPosition: "center" }} />
            <div className="p-5">
              <div className="font-fredoka font-bold text-lg text-arc-text">{it.name}</div>
              <p className="text-sm text-arc-muted mt-1 line-clamp-2">{it.description}</p>
              <div className="flex items-center justify-between mt-4">
                <div className="font-fredoka font-bold text-xl text-arc-secondary"><ArcSymbol />{it.price}</div>
                <button data-testid={`buy-${it.id}`} onClick={() => buy(it.id)} disabled={user?.balance < it.price || it.stock <= 0} className="arc-btn arc-btn-primary text-sm py-2 px-5 disabled:opacity-50">
                  {it.stock <= 0 ? "Esgotado" : "Comprar"}
                </button>
              </div>
              <div className="text-xs text-arc-muted mt-2">Estoque: {it.stock}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </Shell>
  );
}

export function StudentSavings() {
  const { user, refresh } = useAuth();
  const [amount, setAmount] = useState("");
  const [msg, setMsg] = useState("");
  const action = async (op) => {
    try { await axios.post(`${API}/student/savings/${op}`, { amount: parseFloat(amount) }); setMsg(op === "deposit" ? "Depositado na poupança!" : "Resgatado com sucesso!"); setAmount(""); await refresh(); }
    catch (e) { setMsg(e?.response?.data?.detail || "Erro"); }
    setTimeout(() => setMsg(""), 3000);
  };
  const projected = (user?.savings || 0) * Math.pow(1.02, 30);
  return (
    <Shell nav={NAV} title="Poupança">
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">🐷 Minha Poupança</h2>
      {msg && <div className="mb-4 p-4 rounded-2xl bg-arc-success text-arc-text font-semibold">{msg}</div>}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="arc-card p-8 text-center" style={{ background: "linear-gradient(135deg,#FFF5D6 0%,#FFE39A 100%)" }}>
          <ArcoinMascot size={100} className="mx-auto animate-float" />
          <div className="mt-4 text-sm font-semibold text-arc-muted uppercase">Saldo poupado</div>
          <div className="font-fredoka font-bold text-5xl text-arc-text mt-2"><ArcSymbol />{user?.savings?.toFixed(2) || "0.00"}</div>
          <div className="mt-3 text-sm text-arc-muted">Projeção em 30 dias (2%/dia simulado): <strong className="text-arc-success"><ArcSymbol />{projected.toFixed(2)}</strong></div>
        </div>
        <div className="arc-card p-6">
          <h3 className="font-fredoka font-bold text-lg text-arc-text mb-3">Movimentar poupança</h3>
          <p className="text-sm text-arc-muted mb-4">Dinheiro guardado rende um pouquinho a cada dia. Guarde para conquistar itens maiores!</p>
          <input data-testid="savings-amount" type="number" step="0.01" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Valor em Arc" className="arc-input mb-3" />
          <div className="flex gap-3">
            <button data-testid="deposit-btn" onClick={() => action("deposit")} disabled={!amount} className="arc-btn arc-btn-success flex-1 disabled:opacity-50">Depositar</button>
            <button data-testid="withdraw-btn" onClick={() => action("withdraw")} disabled={!amount} className="arc-btn arc-btn-outline flex-1 disabled:opacity-50">Resgatar</button>
          </div>
          <div className="mt-6 p-4 bg-arc rounded-2xl text-sm text-arc-text">
            💡 <strong>Educação financeira:</strong> Poupar é guardar parte do que ganhou para realizar sonhos maiores no futuro.
          </div>
        </div>
      </div>
    </Shell>
  );
}
