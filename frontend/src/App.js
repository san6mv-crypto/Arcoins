import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Login from "./pages/Login";
import { StudentHome, StudentExtrato, StudentChallenges, StudentStore, StudentSavings } from "./pages/Student";
import { TeacherHome, TeacherCreate, TeacherApprovals } from "./pages/Teacher";
import { AdminHome, AdminUsers, AdminClasses, AdminStore, AdminConfig } from "./pages/Admin";
import "./index.css";

function Guard({ roles, children }) {
  const { user } = useAuth();
  if (user === undefined) return <div className="min-h-screen flex items-center justify-center bg-arc"><div className="font-fredoka text-2xl text-arc-text">Carregando...</div></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    const redir = user.role === "student" ? "/aluno" : user.role === "teacher" ? "/professor" : "/admin";
    return <Navigate to={redir} replace />;
  }
  return children;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (user === undefined) return null;
  if (!user) return <Navigate to="/login" replace />;
  const p = user.role === "student" ? "/aluno" : user.role === "teacher" ? "/professor" : "/admin";
  return <Navigate to={p} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/aluno" element={<Guard roles={["student"]}><StudentHome /></Guard>} />
          <Route path="/aluno/extrato" element={<Guard roles={["student"]}><StudentExtrato /></Guard>} />
          <Route path="/aluno/desafios" element={<Guard roles={["student"]}><StudentChallenges /></Guard>} />
          <Route path="/aluno/loja" element={<Guard roles={["student"]}><StudentStore /></Guard>} />
          <Route path="/aluno/poupanca" element={<Guard roles={["student"]}><StudentSavings /></Guard>} />
          <Route path="/professor" element={<Guard roles={["teacher"]}><TeacherHome /></Guard>} />
          <Route path="/professor/criar" element={<Guard roles={["teacher"]}><TeacherCreate /></Guard>} />
          <Route path="/professor/aprovacoes" element={<Guard roles={["teacher"]}><TeacherApprovals /></Guard>} />
          <Route path="/admin" element={<Guard roles={["admin"]}><AdminHome /></Guard>} />
          <Route path="/admin/usuarios" element={<Guard roles={["admin"]}><AdminUsers /></Guard>} />
          <Route path="/admin/turmas" element={<Guard roles={["admin"]}><AdminClasses /></Guard>} />
          <Route path="/admin/loja" element={<Guard roles={["admin"]}><AdminStore /></Guard>} />
          <Route path="/admin/config" element={<Guard roles={["admin"]}><AdminConfig /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
