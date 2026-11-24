import { Navigate, Route, Routes } from "react-router";
import { RequireAuth } from "./auth/RequireAuth";
import { Layout } from "./components/Layout";
import { UnscoredGate } from "./components/UnscoredGate";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Norms } from "./pages/Norms";
import { ProcessActivities } from "./pages/ProcessActivities";
import { ProcessBoard } from "./pages/ProcessBoard";
import { ProcessDocuments } from "./pages/ProcessDocuments";
import { ProcessDossier } from "./pages/ProcessDossier";
import { ProcessGenerated } from "./pages/ProcessGenerated";
import { ProcessScoring } from "./pages/ProcessScoring";
import { ProcessStep1 } from "./pages/ProcessStep1";
import { ProfessorForm } from "./pages/ProfessorForm";
import { ScoringAdmin } from "./pages/ScoringAdmin";

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
        <Route path="processos/:id/documentos" element={<ProcessDocuments />} />
        <Route path="processos/:id/atividades" element={<ProcessActivities />} />
        <Route path="processos/:id/pontuacao" element={<ProcessScoring />} />
        <Route
          path="processos/:id/gerados"
          element={
            <UnscoredGate step={5} title="Documentos gerados">
              <ProcessGenerated />
            </UnscoredGate>
          }
        />
        <Route
          path="processos/:id/banca"
          element={
            <UnscoredGate step={6} title="Banca e Parecer">
              <ProcessBoard />
            </UnscoredGate>
          }
        />
        <Route
          path="processos/:id/dossie"
          element={
            <UnscoredGate step={7} title="Requerimento e dossiê">
              <ProcessDossier />
            </UnscoredGate>
          }
        />
        <Route path="normas" element={<Norms />} />
        <Route path="administracao/tabelas" element={<ScoringAdmin />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
