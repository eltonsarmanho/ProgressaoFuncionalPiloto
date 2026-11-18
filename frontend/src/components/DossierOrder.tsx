import { useEffect, useState } from "react";
import { errorMessage, request } from "../api/client";
import type { DossierItem } from "../api/generated";
import { DOCUMENT_KIND_LABELS } from "../labels";

/**
 * ORD-01: the order in which the documents of the dossier go, as the configuration file of the server
 * lists it (never typed here), with the three documents the system generates marked.
 */
export function DossierOrder() {
  const [items, setItems] = useState<DossierItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    request<DossierItem[]>("GET", "/api/dossier-order")
      .then((found) => {
        if (!cancelled) setItems(found);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="card" aria-labelledby="dossier-title">
      <h2 id="dossier-title">Ordem do dossiê</h2>
      <p className="muted">Lembrete da ordem de entrega: o sistema gera só os documentos marcados.</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {items && (
        <ol aria-label="Ordem de entrega do dossiê" className="dossier-list">
          {items.map((item) => (
            <li key={item.order} value={item.order}>
              {item.title}
              {item.generated_by && (
                <>
                  {" "}
                  <span className="badge">Gerado pelo sistema</span>
                  <small className="muted">{` ${DOCUMENT_KIND_LABELS[item.generated_by]}`}</small>
                </>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
