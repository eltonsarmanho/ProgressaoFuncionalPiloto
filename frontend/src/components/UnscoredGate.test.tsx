import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { mockFetch } from "../test/fetchMock";
import { countUnscored } from "../unscored";
import { UnscoredGate } from "./UnscoredGate";

const row = (status: string) => ({ activity_id: status, title: status, status });
const process = (status: string) => ({ status: 200, body: { id: "p1", status } });
const scoring = (...statuses: string[]) => ({ status: 200, body: { rows: statuses.map(row) } });

function renderGate(step = 5) {
  return render(
    <MemoryRouter initialEntries={["/processos/p1/gerados"]}>
      <Routes>
        <Route
          path="processos/:id/gerados"
          element={
            <UnscoredGate step={step} title="Documentos gerados">
              <p>Conteúdo da etapa</p>
            </UnscoredGate>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("countUnscored", () => {
  it("conta só o que não é PONTUADA", () => {
    expect(countUnscored([row("PONTUADA"), row("POTENCIAL"), row("NAO_PONTUADA"), row("REJEITADA")])).toBe(3);
    expect(countUnscored([])).toBe(0);
  });
});

describe("UnscoredGate: a tela fica fechada com atividade não pontuada", () => {
  it("mostra o aviso e o caminho de volta à Etapa 4, sem o conteúdo da etapa", async () => {
    mockFetch({
      "GET /api/processes/p1": process("EM_ANDAMENTO"),
      "GET /api/processes/p1/scoring": scoring("PONTUADA", "POTENCIAL", "NAO_PONTUADA"),
    });
    renderGate();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Há 2 atividades não pontuadas na Etapa 4. Valide ou rejeite essas atividades para abrir esta etapa.",
    );
    expect(screen.queryByText("Conteúdo da etapa")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Etapa 5 · Documentos gerados" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar à Etapa 4 · Pontuação" })).toHaveAttribute("href", "/processos/p1/pontuacao");
  });

  it("com 1 atividade usa o singular", async () => {
    mockFetch({ "GET /api/processes/p1": process("EM_ANDAMENTO"), "GET /api/processes/p1/scoring": scoring("POTENCIAL") });
    renderGate();
    expect(await screen.findByRole("alert")).toHaveTextContent("Há 1 atividade não pontuada na Etapa 4.");
  });

  it("com todas pontuadas (a rejeitada não entra na pontuação) abre a etapa", async () => {
    mockFetch({ "GET /api/processes/p1": process("EM_ANDAMENTO"), "GET /api/processes/p1/scoring": scoring("PONTUADA", "PONTUADA") });
    renderGate();
    expect(await screen.findByText("Conteúdo da etapa")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("processo concluído ou arquivado é só leitura: não fecha, e nem consulta a pontuação", async () => {
    for (const status of ["CONCLUIDO", "ARQUIVADO"]) {
      const { calls } = mockFetch({ "GET /api/processes/p1": process(status) });
      const { unmount } = renderGate();
      expect(await screen.findByText("Conteúdo da etapa")).toBeInTheDocument();
      expect(calls.some((c) => c.path.endsWith("/scoring"))).toBe(false);
      unmount();
    }
  });

  it("se a conferência falha a etapa abre", async () => {
    mockFetch({ "GET /api/processes/p1": process("EM_ANDAMENTO"), "GET /api/processes/p1/scoring": { status: 500, body: { detail: "falha" } } });
    renderGate();
    expect(await screen.findByText("Conteúdo da etapa")).toBeInTheDocument();
  });
});
