import { Navigate, Route, Routes } from "react-router";
import { RequireAuth } from "./auth/RequireAuth";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ProcessStep1 } from "./pages/ProcessStep1";
import { ProfessorForm } from "./pages/ProfessorForm";

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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
