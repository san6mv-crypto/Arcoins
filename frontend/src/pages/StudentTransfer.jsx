import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Confetti from "react-confetti";
import Shell from "../components/Shell";
import { useAuth, API } from "../auth";
import { ArcSymbol } from "../Mascot";

const NAV = [
  { key: "home", label: "Início", to: "/aluno" },
  { key: "extrato", label: "Extrato", to: "/aluno/extrato" },
  { key: "desafios", label: "Desafios", to: "/aluno/desafios" },
  { key: "loja", label: "Loja", to: "/aluno/loja" },
  { key: "poupanca", label: "Poupança", to: "/aluno/poupanca" },
  { key: "transferir", label: "🔁 Transferir", to: "/aluno/transferir" },
];

export default function StudentTransfer() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState({ ra: "", amount: "", message: "" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confetti, setConfetti] = useState(false);
  const [history, setHistory] = useState([]);

  const loadHistory = async () => {
    try {
      const { data } = await axios.get(`${API}/student/transactions`);
      setHistory(data.filter((t) => t.type === "transfer_in" || t.type === "transfer_out").slice(0, 15));
    } catch {}
  };
  useEffect(() => { loadHistory(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setMsg(null); setLoading(true);
    try {
      const { data } = await axios.post(`${API}/student/transfer`, {
        ra: form.ra.trim(),
        amount: parseFloat(form.amount),
        message: form.message.trim(),
      });
      setMsg({ type: "success", text: `🎉 ${data.amount.toFixed(2)} ₡ enviados para ${data.receiver_name}! Novo saldo: ₡ ${data.new_balance.toFixed(2)}` });
      setConfetti(true);
      setTimeout(() => setConfetti(false), 3500);
      setForm({ ra: "", amount: "", message: "" });
      await refresh();
      loadHistory();
    } catch (err) {
      setMsg({ type: "error", text: err?.response?.data?.detail || "Erro na transferência" });
    } finally {
      setLoading(false);
      setTimeout(() => setMsg(null), 5000);
    }
  };

  return (
    <Shell nav={NAV} title="Transferir Arc">
      {confetti && <Confetti numberOfPieces={220} recycle={false} />}
      <h2 className="font-fredoka font-bold text-2xl text-arc-text mb-6">🔁 Enviar Arc para outro aluno</h2>

      {msg && (
        <div className={`mb-4 p-4 rounded-2xl font-semibold ${msg.type === "success" ? "bg-arc-success text-arc-text" : "bg-pink-100 text-arc-accent"}`} data-testid="transfer-msg">
          {msg.text}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Balance card */}
        <motion.div className="arc-card p-6" style={{ background: "linear-gradient(135deg,#00B4D8 0%,#0096C7 100%)", color: "#fff" }}>
          <div className="text-sm opacity-90 font-semibold uppercase">Seu saldo disponível</div>
          <div className="font-fredoka font-bold text-4xl mt-2"><span style={{ color: "#FFBE0B" }}>₡</span> {user?.balance?.toFixed(2)}</div>
          <div className="mt-3 text-xs opacity-90">Seu RA: <strong>{user?.ra || "—"}</strong></div>
          <div className="mt-4 text-xs opacity-90 leading-relaxed">💡 Compartilhe seu RA com um colega para receber Arc dele. As transferências aparecem no seu extrato.</div>
        </motion.div>

        {/* Transfer form */}
        <form onSubmit={submit} className="arc-card p-6 lg:col-span-2 space-y-4" data-testid="transfer-form">
          <h3 className="font-fredoka font-bold text-lg text-arc-text">Nova transferência</h3>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">RA do destinatário</label>
            <input required data-testid="transfer-ra" className="arc-input mt-1 font-mono" placeholder="Ex: 2026001" value={form.ra} onChange={(e) => setForm({ ...form, ra: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">Valor (₡)</label>
            <input required type="number" step="1" min="1" max={user?.balance || 0} data-testid="transfer-amount" className="arc-input mt-1" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-arc-muted uppercase">Mensagem (opcional, máx 120)</label>
            <input maxLength={120} data-testid="transfer-msg-input" className="arc-input mt-1" placeholder="Ex: Obrigado pela ajuda!" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
          </div>
          <button type="submit" data-testid="transfer-submit" disabled={loading || !form.ra || !form.amount} className="arc-btn arc-btn-primary w-full disabled:opacity-50">
            {loading ? "Enviando..." : `Enviar ₡ ${form.amount || "0"} 🚀`}
          </button>
          <div className="text-xs text-arc-muted bg-arc p-3 rounded-2xl">
            ⚠️ A transferência é <strong>imediata e irreversível</strong>. Confira o RA antes de enviar.
          </div>
        </form>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="mt-8">
          <h3 className="font-fredoka font-bold text-lg text-arc-text mb-3">📜 Suas transferências recentes</h3>
          <div className="arc-card p-4 md:p-6">
            <div className="space-y-2" data-testid="transfer-history">
              {history.map((t) => (
                <div key={t.id} className="flex items-center justify-between p-3 rounded-2xl bg-arc">
                  <div className="flex items-center gap-3">
                    <div className={`text-2xl`}>{t.type === "transfer_in" ? "📥" : "📤"}</div>
                    <div>
                      <div className="font-semibold text-arc-text text-sm">{t.description}</div>
                      <div className="text-xs text-arc-muted">{new Date(t.created_at).toLocaleString("pt-BR")}</div>
                    </div>
                  </div>
                  <div className={`font-fredoka font-bold ${t.amount >= 0 ? "text-arc-success" : "text-arc-accent"}`}>
                    {t.amount >= 0 ? "+" : ""}{t.amount.toFixed(2)} <ArcSymbol />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
