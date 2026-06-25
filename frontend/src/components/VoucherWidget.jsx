import React, { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Confetti from "react-confetti";
import { useAuth, API } from "../auth";
import { ArcSymbol } from "../Mascot";

export default function VoucherWidget() {
  const { refresh } = useAuth();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confetti, setConfetti] = useState(false);

  const redeem = async (e) => {
    e.preventDefault();
    setLoading(true); setMsg(null);
    try {
      const { data } = await axios.post(`${API}/student/vouchers/redeem`, { code: code.trim().toUpperCase() });
      setMsg({ type: "success", text: `🎉 Voucher resgatado! +₡${data.value} ${data.description ? `(${data.description})` : ""}` });
      setCode("");
      setConfetti(true);
      setTimeout(() => setConfetti(false), 3500);
      await refresh();
    } catch (err) {
      setMsg({ type: "error", text: err?.response?.data?.detail || "Código inválido" });
    } finally {
      setLoading(false);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="arc-card p-6 relative overflow-hidden"
      style={{ background: "linear-gradient(135deg,#FFBE0B 0%,#FF006E 130%)", color: "#fff" }}
      data-testid="voucher-widget"
    >
      {confetti && <Confetti numberOfPieces={180} recycle={false} />}
      <div className="flex items-center gap-3 mb-3">
        <div className="text-3xl">🎟️</div>
        <div>
          <h3 className="font-fredoka font-bold text-lg">Resgatar voucher</h3>
          <p className="text-xs opacity-90">Tem um código do seu professor? Ganhe ₡ Arc extra!</p>
        </div>
      </div>
      <form onSubmit={redeem} className="flex gap-2">
        <input
          data-testid="redeem-code-input"
          required
          maxLength={20}
          placeholder="DIGITE O CÓDIGO"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          className="arc-input flex-1 font-mono tracking-widest text-center font-bold"
          style={{ background: "rgba(255,255,255,0.95)", color: "#073B4C" }}
        />
        <button
          data-testid="redeem-btn"
          type="submit"
          disabled={loading || !code.trim()}
          className="arc-btn px-5 disabled:opacity-50"
          style={{ background: "#073B4C", color: "#FFBE0B" }}
        >
          {loading ? "..." : "Resgatar"}
        </button>
      </form>
      {msg && (
        <div className={`mt-3 p-3 rounded-2xl text-sm font-semibold ${msg.type === "success" ? "bg-white text-arc-text" : "bg-pink-100 text-arc-accent"}`} data-testid="redeem-msg">
          {msg.text}
        </div>
      )}
    </motion.div>
  );
}
