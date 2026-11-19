import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { MergedRef } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { MergedNote } from "./MergedNote";

const ONE: MergedRef[] = [{ id: "m1", title: "Visão Computacional com OpenCV (cópia)" }];
const TWO: MergedRef[] = [...ONE, { id: "m2", title: "Visão Computacional com OpenCV (outra cópia)" }];

describe("DUP-07: MergedNote", () => {
  it("mostra '1 duplicada mesclada' com o título da mesclada", () => {
    render(<MergedNote merged={ONE} onSeparated={vi.fn()} />);
    expect(screen.getByText("1 duplicada mesclada")).toBeInTheDocument();
    expect(screen.getByText("Visão Computacional com OpenCV (cópia)")).toBeInTheDocument();
  });

  it("mostra '2 duplicadas mescladas' com os dois títulos e um botão por mesclada", () => {
    render(<MergedNote merged={TWO} onSeparated={vi.fn()} />);
    expect(screen.getByText("2 duplicadas mescladas")).toBeInTheDocument();
    expect(screen.getByText("Visão Computacional com OpenCV (cópia)")).toBeInTheDocument();
    expect(screen.getByText("Visão Computacional com OpenCV (outra cópia)")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Não é duplicada/ })).toHaveLength(2);
  });

  it("sem mescladas não renderiza nada", () => {
    const { container } = render(<MergedNote merged={[]} onSeparated={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("'Não é duplicada' chama POST /api/activities/{id}/separate da mesclada e avisa o pai", async () => {
    setCsrfToken("tok");
    const restored = { id: "m2", title: "Visão Computacional com OpenCV (outra cópia)" };
    const { calls } = mockFetch({ "POST /api/activities/m2/separate": { status: 200, body: restored } });
    const onSeparated = vi.fn();
    const user = userEvent.setup();
    render(<MergedNote merged={TWO} onSeparated={onSeparated} />);
    await user.click(screen.getByRole("button", { name: "Não é duplicada: Visão Computacional com OpenCV (outra cópia)" }));
    await waitFor(() => expect(onSeparated).toHaveBeenCalledTimes(1));
    expect(onSeparated).toHaveBeenCalledWith(restored);
    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("POST");
    expect(calls[0].path).toBe("/api/activities/m2/separate");
    expect(new Headers(calls[0].init?.headers).get("X-CSRF-Token")).toBe("tok");
  });

  it("erro 409 mostra a mensagem do servidor e não avisa o pai", async () => {
    setCsrfToken("tok");
    mockFetch({
      "POST /api/activities/m1/separate": { status: 409, body: { detail: "A atividade foi alterada por outro usuário; recarregue" } },
    });
    const onSeparated = vi.fn();
    const user = userEvent.setup();
    render(<MergedNote merged={ONE} onSeparated={onSeparated} />);
    await user.click(screen.getByRole("button", { name: /Não é duplicada/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade foi alterada por outro usuário; recarregue");
    expect(onSeparated).not.toHaveBeenCalled();
  });

  it("erro 422 mostra a mensagem do campo", async () => {
    setCsrfToken("tok");
    mockFetch({
      "POST /api/activities/m1/separate": {
        status: 422,
        body: { detail: [{ field: "atividade", code: "VALIDACAO", message: "A atividade não foi mesclada" }] },
      },
    });
    const user = userEvent.setup();
    render(<MergedNote merged={ONE} onSeparated={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /Não é duplicada/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade não foi mesclada");
  });
});
