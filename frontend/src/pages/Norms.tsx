import { useCallback, useEffect, useState } from "react";
import { ApiError, errorMessage, request } from "../api/client";
import type { Norm } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Modal } from "../components/Modal";
import { NormFileForm, NormForm } from "../components/NormForms";
import { NormLink } from "../components/NormLink";
import { LINKED_RULE_LABELS, NORM_KIND_LABELS, formatDate } from "../labels";

type Dialog =
  | { kind: "create" }
  | { kind: "edit"; norm: Norm }
  | { kind: "file"; norm: Norm }
  | { kind: "archive"; norm: Norm };

/** NLIST-01: "a partir de", "até" or the closed range; "—" when the norm has no validity. */
function validity(norm: Norm): string {
  if (norm.valid_from && norm.valid_to) return `${formatDate(norm.valid_from)} a ${formatDate(norm.valid_to)}`;
  if (norm.valid_from) return `a partir de ${formatDate(norm.valid_from)}`;
  if (norm.valid_to) return `até ${formatDate(norm.valid_to)}`;
  return "—";
}

/** NBASE-08: the only question before archiving; the norm stays cited by its rules. */
function ArchiveDialog({
  norm,
  onArchived,
  onStale,
  onClose,
}: {
  norm: Norm;
  onArchived: () => void;
  onStale: () => void;
  onClose: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setError(null);
    setBusy(true);
    try {
      await request<Norm>("POST", `/api/norms/${norm.id}/archive`, { expected_version: norm.version });
      onArchived();
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 409) {
        setError("A norma foi alterada por outra pessoa; recarregue");
        onStale();
      } else {
        setError(errorMessage(err));
      }
    }
  }

  return (
    <Modal title="Arquivar norma" onClose={onClose}>
      <p>
        Arquivar a norma {norm.title}? Ela sai da lista padrão e continua citada nas regras e nos alertas, com
        &quot;(arquivada)&quot;.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>
          Arquivar
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </Modal>
  );
}

/**
 * NLIST-01..03: the norms of the system for everyone, with their rules; only ADMIN registers, edits,
 * attaches the PDF and archives. Archived norms show with "Mostrar arquivadas".
 */
export function Norms() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const [norms, setNorms] = useState<Norm[] | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    request<Norm[]>("GET", `/api/norms?include_archived=${showArchived}`)
      .then((all) => {
        setNorms(all);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [showArchived]);

  useEffect(reload, [reload]);

  function saved() {
    setDialog(null);
    reload();
  }

  if (!norms) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p className="muted">Carregando…</p>
    );
  }

  return (
    <>
      <h1>Normas</h1>
      <p className="muted">As normas que fundamentam as regras do sistema, com a fonte e as regras ligadas a cada uma.</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="btn-row">
        <label>
          <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> Mostrar
          arquivadas
        </label>
        {isAdmin && (
          <button type="button" className="btn btn-primary" onClick={() => setDialog({ kind: "create" })}>
            Cadastrar norma
          </button>
        )}
      </div>
      {norms.length === 0 ? (
        <p className="muted">Nenhuma norma cadastrada.</p>
      ) : (
        <table className="scoring-table">
          <thead>
            <tr>
              <th>Norma</th>
              <th>Tipo</th>
              <th>Órgão</th>
              <th>Publicação</th>
              <th>Vigência</th>
              <th>Regras ligadas</th>
              {isAdmin && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {norms.map((n) => (
              <tr key={n.id}>
                <td data-label="Norma">
                  <NormLink title={n.title} url={n.source_url} fileUrl={n.file?.url ?? null} archived={n.archived} />
                  <br />
                  <small className="muted">{n.code}</small>
                </td>
                <td data-label="Tipo">{NORM_KIND_LABELS[n.kind]}</td>
                <td data-label="Órgão">{n.issuer}</td>
                <td data-label="Publicação">{formatDate(n.published_on)}</td>
                <td data-label="Vigência">{validity(n)}</td>
                <td data-label="Regras ligadas">
                  {n.linked_rules.length === 0 ? (
                    "—"
                  ) : (
                    <ul>
                      {n.linked_rules.map((r, i) => (
                        <li key={`${r.kind}-${r.name}-${i}`}>
                          {LINKED_RULE_LABELS[r.kind] ?? r.kind}: {r.name}
                          {r.detail ? ` (${r.detail})` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
                {isAdmin && (
                  <td data-label="Ações">
                    <div className="btn-row">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        aria-label={`Editar ${n.title}`}
                        title={`Editar ${n.title}`}
                        onClick={() => setDialog({ kind: "edit", norm: n })}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        aria-label={`Anexar PDF a ${n.title}`}
                        title={`Anexar PDF a ${n.title}`}
                        onClick={() => setDialog({ kind: "file", norm: n })}
                      >
                        Anexar PDF
                      </button>
                      {!n.archived && (
                        <button
                          type="button"
                          className="btn btn-danger"
                          aria-label={`Arquivar ${n.title}`}
                          title={`Arquivar ${n.title}`}
                          onClick={() => setDialog({ kind: "archive", norm: n })}
                        >
                          Arquivar
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {dialog?.kind === "create" && (
        <Modal title="Cadastrar norma" onClose={() => setDialog(null)}>
          <NormForm onSaved={saved} onCancel={() => setDialog(null)} />
        </Modal>
      )}
      {dialog?.kind === "edit" && (
        <Modal title="Editar norma" onClose={() => setDialog(null)}>
          <NormForm norm={dialog.norm} onSaved={saved} onCancel={() => setDialog(null)} />
        </Modal>
      )}
      {dialog?.kind === "file" && (
        <Modal title="Anexar PDF" onClose={() => setDialog(null)}>
          <NormFileForm norm={dialog.norm} onSaved={saved} onCancel={() => setDialog(null)} />
        </Modal>
      )}
      {dialog?.kind === "archive" && (
        <ArchiveDialog norm={dialog.norm} onArchived={saved} onStale={reload} onClose={() => setDialog(null)} />
      )}
    </>
  );
}
