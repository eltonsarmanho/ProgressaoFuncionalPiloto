import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { Opinion } from "../api/board";
import { opinion } from "../test/boardFixtures";
import { mockFetch } from "../test/fetchMock";
import { OpinionForm } from "./OpinionForm";

const PATH = "PUT /api/processes/p1/board/opinion";
const REASON = "O processo está concluído ou arquivado e não aceita alterações.";

function Harness({ initial, onSeen, onStale, ...rest }: { initial: Opinion; onSeen?: (o: Opinion) => void; onStale?: () => void; readOnly?: boolean; readOnlyReason?: string }) {
  const [current, setCurrent] = useState(initial);
  return (
    <OpinionForm
      processId="p1"
      opinion={current}
      onChanged={(next) => {
        setCurrent(next);
        onSeen?.(next);
      }}
      onStale={onStale}
      {...rest}
    />
  );
}

const favorable = () => screen.getByRole("radio", { name: "Favorável" });
const unfavorable = () => screen.getByRole("radio", { name: "Desfavorável" });
const save = () => screen.getByRole("button", { name: "Salvar minuta do Parecer" });
const setNotes = (text: string) => fireEvent.change(screen.getByLabelText("Observações da banca"), { target: { value: text } });

describe("PAR-01, PAR-12: a conclusão não vem escolhida", () => {
  it("com a minuta vazia nenhum botão de rádio está marcado e nada é pedido ao servidor", () => {
    const { fn } = mockFetch({});
    render(<Harness initial={opinion()} />);
    expect(screen.getAllByRole("radio")).toHaveLength(2);
    expect(favorable()).not.toBeChecked();
    expect(unfavorable()).not.toBeChecked();
    expect(fn).not.toHaveBeenCalled();
  });

  it("PAR-12: a tela não sugere conclusão: mesmo com data, local e observações preenchidos nenhuma vem marcada", () => {
    render(<Harness initial={opinion({ opinion_date: "2026-11-20", place: "Belém", notes: "Pontuação acima do mínimo.", version: 2 })} />);
    expect(favorable()).not.toBeChecked();
    expect(unfavorable()).not.toBeChecked();
  });

  it("uma conclusão já salva aparece marcada", () => {
    render(<Harness initial={opinion({ conclusion: "DESFAVORAVEL", version: 2 })} />);
    expect(unfavorable()).toBeChecked();
    expect(favorable()).not.toBeChecked();
  });

  it("PAR-01: escolher 'Favorável' e salvar envia a conclusão com a data, o local, as observações e a versão", async () => {
    const saved = opinion({ conclusion: "FAVORAVEL", opinion_date: "2026-11-20", place: "Belém", notes: "Sem ressalvas.", version: 1 });
    const { calls } = mockFetch({ [PATH]: { status: 200, body: saved } });
    const seen = vi.fn();
    render(<Harness initial={opinion()} onSeen={seen} />);
    await userEvent.click(favorable());
    await userEvent.type(screen.getByLabelText("Data do Parecer"), "2026-11-20");
    await userEvent.type(screen.getByLabelText("Local"), "Belém");
    setNotes("Sem ressalvas.");
    await userEvent.click(save());
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      conclusion: "FAVORAVEL",
      opinion_date: "2026-11-20",
      place: "Belém",
      notes: "Sem ressalvas.",
      expected_version: 0,
    });
    await waitFor(() => expect(seen).toHaveBeenCalledWith(saved));
    expect(favorable()).toBeChecked();
  });

  it("salvar sem escolher a conclusão envia conclusion nulo, sem preencher nada", async () => {
    const { calls } = mockFetch({ [PATH]: { status: 200, body: opinion({ place: "Belém", version: 1 }) } });
    render(<Harness initial={opinion()} />);
    await userEvent.type(screen.getByLabelText("Local"), "Belém");
    await userEvent.click(save());
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      conclusion: null,
      opinion_date: null,
      place: "Belém",
      notes: null,
      expected_version: 0,
    });
  });
});

describe("PAR-13: limites", () => {
  it("o contador mostra '4 998 / 5 000' com 2 caracteres a menos que o limite", () => {
    render(<Harness initial={opinion()} />);
    expect(screen.getByText("0 / 5 000")).toBeInTheDocument();
    setNotes("a".repeat(4998));
    expect(screen.getByText("4 998 / 5 000")).toBeInTheDocument();
    expect(save()).toBeEnabled();
  });

  it("acima de 5 000 o contador avisa e o salvar fica bloqueado", () => {
    render(<Harness initial={opinion()} />);
    setNotes("a".repeat(5001));
    expect(screen.getByText("5 001 / 5 000")).toHaveClass("error");
    expect(save()).toBeDisabled();
    setNotes("a".repeat(5000));
    expect(screen.getByText("5 000 / 5 000")).not.toHaveClass("error");
    expect(save()).toBeEnabled();
  });

  it("422 de place e de notes aparecem junto do campo", async () => {
    mockFetch({
      [PATH]: {
        status: 422,
        body: {
          detail: [
            { field: "place", message: "Local deve ter até 100 caracteres" },
            { field: "notes", message: "Observações devem ter até 5000 caracteres" },
          ],
        },
      },
    });
    render(<Harness initial={opinion()} />);
    await userEvent.click(save());
    expect(await screen.findByLabelText("Local")).toHaveAccessibleDescription("Local deve ter até 100 caracteres");
    expect(screen.getByLabelText("Observações da banca")).toHaveAccessibleDescription(/Observações devem ter até 5000 caracteres/);
    expect(screen.getByLabelText("Local")).toBeInvalid();
  });

  it("409 mostra o texto de recarregar e avisa a página", async () => {
    mockFetch({ [PATH]: { status: 409, body: { detail: "A minuta foi alterada por outro usuário", code: "VERSAO_DESATUALIZADA" } } });
    const onStale = vi.fn();
    render(<Harness initial={opinion({ version: 2 })} onStale={onStale} />);
    await userEvent.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("Os dados foram alterados por outra pessoa; recarregue");
    expect(onStale).toHaveBeenCalledTimes(1);
  });
});

describe("BNAV-02: somente leitura", () => {
  it("desabilita a conclusão, a data, o local, as observações e o salvar, com o motivo", () => {
    render(<Harness initial={opinion({ conclusion: "FAVORAVEL", version: 2 })} readOnly readOnlyReason={REASON} />);
    expect(screen.getByText(REASON)).toBeInTheDocument();
    expect(favorable()).toBeDisabled();
    expect(unfavorable()).toBeDisabled();
    expect(screen.getByLabelText("Data do Parecer")).toBeDisabled();
    expect(screen.getByLabelText("Local")).toBeDisabled();
    expect(screen.getByLabelText("Observações da banca")).toBeDisabled();
    expect(save()).toBeDisabled();
  });
});
