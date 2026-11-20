import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import { mockFetch, type MockResponse } from "../test/fetchMock";
import { StartProcessDialog } from "./ProcessDialogs";

const POST = "POST /api/processes/p1/status";
const TEXT =
  "Depois de iniciado, o processo não volta a rascunho e cada alteração na Etapa 1 passa a pedir justificativa.";

function setup(response: MockResponse) {
  setCsrfToken("tok");
  const mock = mockFetch({ [POST]: response });
  const handlers = { onStarted: vi.fn(), onStale: vi.fn(), onClose: vi.fn() };
  render(<StartProcessDialog processId="p1" version={4} {...handlers} />);
  return { ...mock, ...handlers, user: userEvent.setup() };
}

const dialog = () => screen.getByRole("dialog", { name: "Iniciar processo" });
const posts = (calls: { method: string; path: string }[]) => calls.filter((c) => `${c.method} ${c.path}` === POST);

describe("CAINI-03: o modal de iniciar o processo", () => {
  it("mostra o título, o texto exato, Iniciar e Cancelar e nenhum campo de justificativa", () => {
    setup({ status: 200, body: { status: "EM_ANDAMENTO", version: 5 } });
    const d = dialog();
    expect(within(d).getByText(TEXT)).toBeInTheDocument();
    expect(within(d).getByRole("button", { name: "Iniciar" })).toBeInTheDocument();
    expect(within(d).getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
    expect(within(d).queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(within(d).queryByRole("textbox")).not.toBeInTheDocument();
  });
});

describe("CAINI-04: o pedido ao confirmar", () => {
  it("envia o status e a versão exibida, sem a chave justificativa, e com 200 chama onStarted com a versão devolvida", async () => {
    const { calls, user, onStarted, onStale } = setup({ status: 200, body: { status: "EM_ANDAMENTO", version: 5 } });
    await user.click(within(dialog()).getByRole("button", { name: "Iniciar" }));
    expect(posts(calls)).toHaveLength(1);
    const body = JSON.parse(String(calls.find((c) => c.method === "POST")?.init?.body));
    expect(body).toEqual({ status: "EM_ANDAMENTO", expected_version: 4 });
    expect("justificativa" in body).toBe(false);
    await vi.waitFor(() => expect(onStarted).toHaveBeenCalledWith("EM_ANDAMENTO", 5));
    expect(onStale).not.toHaveBeenCalled();
  });
});

describe("CAINI-06: 409", () => {
  it("mostra a mensagem do servidor em role=alert e chama onStale", async () => {
    const { user, onStale, onStarted } = setup({ status: 409, body: { detail: "Versão desatualizada do processo." } });
    await user.click(within(dialog()).getByRole("button", { name: "Iniciar" }));
    expect(await within(dialog()).findByRole("alert")).toHaveTextContent("Versão desatualizada do processo.");
    expect(onStale).toHaveBeenCalledTimes(1);
    expect(onStarted).not.toHaveBeenCalled();
  });
});

describe("CAINI-07: 404 e 422", () => {
  it.each([
    [404, { detail: "Processo não encontrado." }, "Processo não encontrado."],
    [422, { detail: "Transição não permitida." }, "Transição não permitida."],
  ])("com %s mostra a mensagem, não chama onStale e deixa Iniciar habilitado", async (status, body, message) => {
    const { user, onStale, onStarted } = setup({ status, body });
    await user.click(within(dialog()).getByRole("button", { name: "Iniciar" }));
    expect(await within(dialog()).findByRole("alert")).toHaveTextContent(message);
    expect(onStale).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
    expect(within(dialog()).getByRole("button", { name: "Iniciar" })).toBeEnabled();
  });
});

describe("CAINI-03: Cancelar", () => {
  it("chama onClose sem requisição", async () => {
    const { calls, user, onClose } = setup({ status: 200, body: { status: "EM_ANDAMENTO", version: 5 } });
    await user.click(within(dialog()).getByRole("button", { name: "Cancelar" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(0);
  });
});
