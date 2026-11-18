import type { DocumentDetail } from "../api/types";
import {
  ACTIVITY_SOURCE_LABELS,
  ACTIVITY_STATUS_LABELS,
  ACTIVE_DOCUMENT_STATUSES,
  DOCUMENT_CODE_LABELS,
  DOCUMENT_STATUS_LABELS,
  TEXT_METHOD_LABELS,
  formatDecimal,
  itemLabel,
} from "../labels";

const INLINE_IMAGES = ["image/jpeg", "image/png"];

/** Only PDF and images are shown inline; anything else gets the text-only fallback (DOC-12). */
function Original({ doc }: { doc: DocumentDetail }) {
  const src = `/api/documents/${doc.id}/file`;
  if (doc.mime === "application/pdf") {
    return <iframe className="doc-frame" src={src} title={`Documento ${doc.original_name}`} />;
  }
  if (INLINE_IMAGES.includes(doc.mime)) {
    return <img className="doc-image" src={src} alt={`Imagem do documento ${doc.original_name}`} />;
  }
  return (
    <p>
      Este tipo de arquivo não pode ser exibido aqui. <a href={`${src}?download=1`}>Baixar {doc.original_name}</a>
    </p>
  );
}

/**
 * TELA-04 / REV-01 / UIM-08: the stored file, the text of each page with its method and confidence, the
 * extracted JSON (read only), the alerts and the activities suggested from this document.
 * The page shows it inside a `Modal`, which gives the title and the close button.
 */
export function DocumentViewer({ doc }: { doc: DocumentDetail }) {
  const processing = ACTIVE_DOCUMENT_STATUSES.includes(doc.status);
  return (
    <div className="viewer">
      <p>
        Status: <strong>{DOCUMENT_STATUS_LABELS[doc.status]}</strong>
      </p>
      <p className="review-note">
        O que a IA leu deste documento é só uma sugestão: nada vale como validado até você revisar.
      </p>

      <Original doc={doc} />

      {processing && <p>Este documento ainda está sendo processado.</p>}

      {doc.alerts.length > 0 && (
        <section aria-labelledby="viewer-alerts">
          <h3 id="viewer-alerts">Avisos</h3>
          <ul>
            {doc.alerts.map((alert, i) => (
              <li key={`${alert.code}-${i}`} className="sev-ALERTA">
                {DOCUMENT_CODE_LABELS[alert.code] ?? alert.code}
                {alert.field && <> (campo: {alert.field})</>}
                {alert.activity_index != null && <> (atividade {alert.activity_index + 1})</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {doc.pages.length > 0 && (
        <section aria-labelledby="viewer-pages">
          <h3 id="viewer-pages">Texto por página</h3>
          <ol className="page-list">
            {doc.pages.map((page) => (
              <li key={page.page_number}>
                <details>
                  <summary>
                    Página {page.page_number} · Método: {TEXT_METHOD_LABELS[page.method] ?? page.method} · Confiança:{" "}
                    {page.ocr_confidence != null ? `${formatDecimal(page.ocr_confidence)}%` : "não se aplica"}
                  </summary>
                  <pre className="page-text" tabIndex={0}>
                    {page.text}
                  </pre>
                </details>
              </li>
            ))}
          </ol>
        </section>
      )}

      {doc.run && (
        <section aria-labelledby="viewer-json">
          <h3 id="viewer-json">JSON extraído (somente leitura)</h3>
          <p className="muted">
            Modelo: {doc.run.model} · {doc.run.duration_ms} ms. Para corrigir um dado, edite a atividade na Etapa 3.
          </p>
          <pre className="page-text" tabIndex={0} data-testid="extracted-json">
            {JSON.stringify(doc.run.raw_json, null, 2)}
          </pre>
        </section>
      )}

      <section aria-labelledby="viewer-activities">
        <h3 id="viewer-activities">Atividades ligadas a este documento</h3>
        {doc.activities.length === 0 ? (
          <p>Nenhuma atividade está ligada a este documento.</p>
        ) : (
          <ul>
            {doc.activities.map((activity) => (
              <li key={activity.id}>
                <strong>{activity.title}</strong> · {itemLabel(activity.group_number, activity.item_number)} ·{" "}
                {ACTIVITY_SOURCE_LABELS[activity.source] ?? activity.source} ·{" "}
                {ACTIVITY_STATUS_LABELS[activity.status] ?? activity.status}
                {activity.evidences.length > 0 && (
                  <ul>
                    {activity.evidences.map((e) => (
                      <li key={e.id}>
                        {e.document_name}, página {e.page}
                        {e.excerpt && <>: “{e.excerpt}”</>}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
