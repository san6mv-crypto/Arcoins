import React, { useState } from "react";
import axios from "axios";
import { API } from "../auth";

export default function BulkImport({ classes, onDone }) {
  const [file, setFile] = useState(null);
  const [classId, setClassId] = useState("");
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const downloadTemplate = () => {
    const csv = "nome,ra\nLucas Pereira,2026001\nMaria Santos,2026002\nJoão Almeida,2026003\n";
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "arcoins_template_alunos.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (classId) fd.append("class_id", classId);
      fd.append("initial_balance", String(balance || 0));
      const { data } = await axios.post(`${API}/admin/students/bulk-import`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      if (onDone) onDone();
    } catch (err) {
      setError(err?.response?.data?.detail || "Erro ao importar CSV");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="arc-card p-6 mb-6" data-testid="bulk-import">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 className="font-fredoka font-bold text-lg text-arc-text">📤 Importar alunos via planilha (CSV)</h3>
          <p className="text-sm text-arc-muted mt-1">Login do aluno será <code className="bg-arc px-2 py-0.5 rounded">@primeiroNome</code> · Senha = RA. Sem possibilidade de trocar senha.</p>
        </div>
        <button onClick={downloadTemplate} data-testid="download-template" className="arc-btn arc-btn-outline text-sm py-2">⬇️ Baixar modelo CSV</button>
      </div>

      <form onSubmit={submit} className="grid md:grid-cols-4 gap-3 mt-4 items-end">
        <div className="md:col-span-2">
          <label className="text-xs font-semibold text-arc-muted uppercase">Arquivo CSV</label>
          <input
            required type="file" accept=".csv,text/csv"
            data-testid="csv-file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="arc-input mt-1 cursor-pointer file:mr-3 file:px-3 file:py-1 file:rounded-full file:border-0 file:bg-arc-primary file:text-white file:font-semibold"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-arc-muted uppercase">Turma (opcional)</label>
          <select data-testid="bulk-class" className="arc-input mt-1" value={classId} onChange={(e) => setClassId(e.target.value)}>
            <option value="">Sem turma</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-arc-muted uppercase">Saldo inicial (₡)</label>
          <input type="number" step="1" min="0" data-testid="bulk-balance" className="arc-input mt-1" value={balance} onChange={(e) => setBalance(e.target.value)} />
        </div>
        <div className="md:col-span-4">
          <button type="submit" data-testid="bulk-submit" disabled={loading || !file} className="arc-btn arc-btn-primary disabled:opacity-50">
            {loading ? "Importando..." : "🚀 Importar alunos"}
          </button>
        </div>
      </form>

      {error && <div className="mt-4 p-4 rounded-2xl bg-pink-100 text-arc-accent font-semibold" data-testid="bulk-error">{error}</div>}

      {result && (
        <div className="mt-5" data-testid="bulk-result">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="p-4 rounded-2xl bg-arc">
              <div className="text-xs text-arc-muted uppercase font-bold">✅ Criados</div>
              <div className="font-fredoka font-bold text-3xl text-arc-success">{result.created_count}</div>
            </div>
            <div className="p-4 rounded-2xl bg-arc">
              <div className="text-xs text-arc-muted uppercase font-bold">⚠️ Ignorados</div>
              <div className="font-fredoka font-bold text-3xl text-arc-accent">{result.skipped_count}</div>
            </div>
          </div>
          {result.created.length > 0 && (
            <div className="mb-4">
              <div className="font-semibold text-sm text-arc-text mb-2">Logins criados:</div>
              <div className="max-h-60 overflow-y-auto space-y-1 text-sm">
                {result.created.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-xl bg-arc">
                    <span className="text-arc-text"><strong>{c.name}</strong> <span className="text-arc-muted">(RA {c.ra})</span></span>
                    <code className="bg-white px-2 py-1 rounded font-bold text-arc-primary">{c.login}</code>
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.skipped.length > 0 && (
            <div>
              <div className="font-semibold text-sm text-arc-text mb-2">Linhas ignoradas:</div>
              <div className="max-h-40 overflow-y-auto space-y-1 text-sm">
                {result.skipped.map((s, i) => (
                  <div key={i} className="p-2 rounded-xl bg-pink-50 text-arc-text">
                    Linha {s.line}: <strong>{s.name || "(sem nome)"}</strong> — {s.reason}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
