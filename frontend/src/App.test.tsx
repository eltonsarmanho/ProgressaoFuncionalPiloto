import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter, useLocation } from "react-router";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ME, UNAUTHENTICATED, mockFetch } from "./test/fetchMock";

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
        <LocationProbe />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("UI-01: rotas protegidas", () => {
  it("redireciona para /login quando não há sessão", async () => {
    mockFetch({ "GET /api/auth/me": UNAUTHENTICATED });
    renderAt("/processos/123");
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/login$/);
  });

  it("exibe a mensagem do backend quando o login responde 401", async () => {
    mockFetch({
      "GET /api/auth/me": UNAUTHENTICATED,
      "POST /api/auth/login": { status: 401, body: { detail: "Usuário ou senha inválidos" } },
    });
    renderAt("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("E-mail"), "x@ufpa.br");
    await user.type(screen.getByLabelText("Senha"), "senha-errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Usuário ou senha inválidos");
  });

  it("após login válido, exibe a área autenticada", async () => {
    let loggedIn = false;
    mockFetch({
      "GET /api/auth/me": () => (loggedIn ? { status: 200, body: ME } : UNAUTHENTICATED),
      "POST /api/auth/login": () => {
        loggedIn = true;
        return { status: 200, body: { id: ME.id, name: ME.name, role: ME.role } };
      },
      "GET /api/processes": { status: 200, body: [] },
    });
    renderAt("/");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("E-mail"), "admin@ufpa.br");
    await user.type(screen.getByLabelText("Senha"), "senha-correta-123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Admin")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/$/);
  });
});
