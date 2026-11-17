import { Navigate, Route, Routes } from "react-router";
import type { ReactNode } from "react";
import { useAuth } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ProcessScoring } from "./pages/ProcessScoring";
import { ProcessStep1 } from "./pages/ProcessStep1";
import { ProfessorForm } from "./pages/ProfessorForm";
import { ScoringAdmin } from "./pages/ScoringAdmin";

/** ADMUI-01: only ADMIN reaches the administration screens; everyone else goes home. */
function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === "ADMIN" ? children : <Navigate to="/" replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="professores/novo" element={<ProfessorForm />} />
        <Route path="professores/:id" element={<ProfessorForm />} />
        <Route path="processos/novo" element={<ProcessStep1 />} />
        <Route path="processos/:id" element={<ProcessStep1 />} />
        <Route path="processos/:id/pontuacao" element={<ProcessScoring />} />
        <Route
          path="administracao/tabelas"
          element={
            <AdminOnly>
              <ScoringAdmin />
            </AdminOnly>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
