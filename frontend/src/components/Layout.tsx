import { Link, Outlet } from "react-router";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          Progressão Funcional
        </Link>
        {user?.role === "ADMIN" && <Link to="/administracao/tabelas">Tabelas de pontuação</Link>}
        <span className="user">{user?.name}</span>
        <button type="button" className="link" onClick={() => void logout()}>
          Sair
        </button>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
