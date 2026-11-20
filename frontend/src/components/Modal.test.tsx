import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import css from "../styles.css?raw";
import { Modal } from "./Modal";

function Host({ onClose = () => {} }: { onClose?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Abrir
      </button>
      {open && (
        <Modal
          title="Classificar documento"
          onClose={() => {
            onClose();
            setOpen(false);
          }}
        >
          <label htmlFor="campo">Campo</label>
          <input id="campo" />
          <button type="button">Salvar</button>
        </Modal>
      )}
    </>
  );
}

describe("UIM-05: janela acessível", () => {
  it("tem papel de diálogo modal nomeado pelo título e leva o foco para dentro", async () => {
    const user = userEvent.setup();
    render(<Host />);
    await user.click(screen.getByRole("button", { name: "Abrir" }));

    const dialog = screen.getByRole("dialog", { name: "Classificar documento" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    expect(screen.getByLabelText("Campo")).toHaveFocus();
  });

  it("Esc fecha a janela e devolve o foco ao botão que a abriu", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Host onClose={onClose} />);
    const opener = screen.getByRole("button", { name: "Abrir" });
    await user.click(opener);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("o botão Fechar fecha a janela e devolve o foco ao botão que a abriu", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Host onClose={onClose} />);
    const opener = screen.getByRole("button", { name: "Abrir" });
    await user.click(opener);

    await user.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("Tab no último elemento volta ao primeiro e Shift+Tab no primeiro vai ao último", async () => {
    const user = userEvent.setup();
    render(<Host />);
    await user.click(screen.getByRole("button", { name: "Abrir" }));
    const fechar = screen.getByRole("button", { name: "Fechar" });
    const salvar = screen.getByRole("button", { name: "Salvar" });

    salvar.focus();
    await user.tab();
    expect(fechar).toHaveFocus();

    await user.tab({ shift: true });
    expect(salvar).toHaveFocus();
  });

  it("a rolagem do fundo fica travada enquanto a janela está aberta e é restaurada ao fechar", async () => {
    const user = userEvent.setup();
    render(<Host />);
    expect(document.body.style.overflow).toBe("");
    await user.click(screen.getByRole("button", { name: "Abrir" }));
    expect(document.body.style.overflow).toBe("hidden");
    await user.keyboard("{Escape}");
    expect(document.body.style.overflow).toBe("");
  });

  it("o CSS da janela rola na vertical, ocupa no máximo 44rem e não fixa largura em px", () => {
    const rule = css.match(/\.modal\s*{([^}]*)}/)![1];
    expect(Number(rule.match(/max-width:\s*([\d.]+)rem/)![1])).toBeLessThanOrEqual(44);
    expect(rule).toMatch(/(^|[\s;])width:\s*100%/);
    expect(rule).toMatch(/max-height:[^;]+;\s*overflow-y:\s*auto/);
    expect(css).toMatch(/\.modal-backdrop\s*{[^}]*position:\s*fixed[^}]*inset:\s*0/);
  });
});
