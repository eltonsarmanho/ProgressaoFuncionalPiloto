import { useEffect, useState } from "react";
import { getDossier, setDelivered, type ChecklistItem } from "../api/board";
import { errorMessage } from "../api/client";
import { generationErrorMessage } from "../generationErrors";
import { CHECKLIST_STATE_LABELS } from "../labels";
import { OUTDATED_TABLE_NOTICE } from "./GeneratedBlock";

/**
 * DOS-01 to DOS-06, BNAV-02: the documents of the dossier in the order the configuration file of the
 * server lists them (never typed here), each with where it stands: Gerado (number of the last version
 * and the download links), Registrada (the ordinance of the board), Entregue (marked by the person) or
 * Pendente. The box "Entregue" is only on the items the system does not produce; it saves at once and
 * asks for no justification (regra 5). `refreshKey` makes the list be read again (a document just became
 * ready). In a concluded or archived process the boxes are off with the reason; the links stay.
 */
export function DossierChecklist({
  processId,
  readOnly = false,
  readOnlyReason,
  refreshKey = 0,
}: {
  processId: string;
  readOnly?: boolean;
  readOnlyReason?: string;
  refreshKey?: number;
}) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getDossier(processId)
      .then((found) => {
        if (!cancelled) {
          setItems(found);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [processId, refreshKey]);

  async function mark(item: ChecklistItem, delivered: boolean) {
    setSaveError(null);
    setBusy(true);
    try {
      setItems(await setDelivered(processId, item.key, delivered));
    } catch (err) {
      setSaveError(generationErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="dossier-title">
      <h2 id="dossier-title">Dossiê</h2>
      <p className="muted">
        Ordem de entrega: o sistema gera o Requerimento, a Tabela, o Relatório, o Comprovante e o Parecer; nos demais
        itens, marque "Entregue" quando juntar o documento.
      </p>
      {readOnly && readOnlyReason && <p className="muted">{readOnlyReason}</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {saveError && (
        <p role="alert" className="error">
          {saveError}
        </p>
      )}
      {items && (
        <ol aria-label="Ordem de entrega do dossiê" className="dossier-list">
          {items.map((item) => (
            <li key={item.key} value={item.order}>
              <span>{item.title}</span> <span className="badge" data-testid="checklist-state">{CHECKLIST_STATE_LABELS[item.state]}</span>
              {item.state === "GERADO" && item.version_number !== null && (
                <small className="muted">{` versão ${item.version_number}`}</small>
              )}
              {item.state === "GERADO" && item.generation_id && (
                <span className="row-actions">
                  {(["PDF", "DOCX"] as const).map((format) => (
                    <a
                      key={format}
                      href={`/api/generated-documents/${item.generation_id}/files/${format.toLowerCase()}`}
                      aria-label={`Baixar ${item.title} versão ${item.version_number} em ${format}`}
                    >
                      {format}
                    </a>
                  ))}
                </span>
              )}
              {item.source === "MANUAL" && (
                <label className="check-head">
                  <input
                    type="checkbox"
                    aria-label={`Entregue: ${item.title}`}
                    checked={item.state === "ENTREGUE"}
                    disabled={readOnly || busy}
                    onChange={(e) => void mark(item, e.target.checked)}
                  />
                  Entregue
                </label>
              )}
              {item.outdated_table && <p className="doc-warning sev-ALERTA">{OUTDATED_TABLE_NOTICE}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
