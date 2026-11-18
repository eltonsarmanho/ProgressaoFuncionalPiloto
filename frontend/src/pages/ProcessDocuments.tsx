import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { ApiError, errorMessage, request } from "../api/client";
import type { Activity, DocumentDetail, DocumentSummary, ScoringGroup, ScoringVersion, TableChoice } from "../api/types";
import { ActivityForm } from "../components/ActivityForm";
import { DocumentList } from "../components/DocumentList";
import { DocumentViewer } from "../components/DocumentViewer";
import { Modal } from "../components/Modal";
import { StepNav } from "../components/StepNav";
import { UploadDropzone } from "../components/UploadDropzone";
import { usePolling } from "../hooks/usePolling";
import { ACTIVE_DOCUMENT_STATUSES } from "../labels";

/** The form of a new activity that starts from a document; the document is linked once it is saved. */
function ActivityFromDocument({
  processId,
  doc,
  groups,
  onSaved,
  onCancel,
}: {
  processId: string;
  doc: DocumentSummary;
  groups: ScoringGroup[];
  onSaved: (message: string) => void;
  onCancel: () => void;
}) {
  const [page, setPage] = useState("1");

  async function saved(activity: Activity) {
    try {
      await request("POST", `/api/activities/${activity.id}/evidences`, {
        document_id: doc.id,
        page: Number(page) || 1,
      });
      onSaved(`Atividade “${activity.title}” criada e vinculada a ${doc.original_name}, página ${Number(page) || 1}.`);
    } catch (err) {
      onSaved(
        `Atividade “${activity.title}” criada, mas o documento não foi vinculado (${errorMessage(err)}). Vincule-o na Etapa 3.`,
      );
    }
  }

  return (
    <div>
      <div className="card">
        <p>
          A nova atividade será vinculada a <strong>{doc.original_name}</strong>.
        </p>
        <div className="field">
          <label htmlFor="origin-page">Página do documento de origem</label>
          <input
            id="origin-page"
            type="number"
            min={1}
            max={Math.max(doc.page_count, 1)}
            value={page}
            onChange={(e) => setPage(e.target.value)}
          />
        </div>
      </div>
      <ActivityForm processId={processId} groups={groups} onSaved={(a) => void saved(a)} onCancel={onCancel} />
    </div>
  );
}

/** Etapa 2: upload, the document list with automatic refresh, the viewer and activity creation. */
export function ProcessDocuments() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const viewId = params.get("documento");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [groups, setGroups] = useState<ScoringGroup[]>([]);
  const [creating, setCreating] = useState<DocumentSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);

  const reload = () => setReloads((n) => n + 1);
  const polling = documents.some((d) => ACTIVE_DOCUMENT_STATUSES.includes(d.status));

  useEffect(() => {
    let cancelled = false;
    request<DocumentSummary[]>("GET", `/api/processes/${id}/documents`)
      .then((found) => {
        if (cancelled) return;
        setDocuments(found);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloads]);

  // TELA-03: the list reloads while a document is still pending or processing
  usePolling(reload, polling);

  useEffect(() => {
    if (!viewId) return;
    let cancelled = false;
    request<DocumentDetail>("GET", `/api/documents/${viewId}`)
      .then((found) => {
        if (!cancelled) setDetail(found);
      })
      .catch((err) => {
        if (cancelled) return;
        setDetail(null);
        // A document that no longer exists (deleted here or elsewhere) just closes the viewer.
        if (err instanceof ApiError && err.status === 404) setParams({});
        else setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [viewId, reloads, setParams]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const table = await request<TableChoice>("GET", `/api/processes/${id}/scoring/table`);
      const versionId = table.chosen?.version.id ?? table.suggested?.version.id;
      return versionId ? await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`) : null;
    })()
      .then((version) => {
        if (!cancelled) setGroups(version?.groups ?? []);
      })
      .catch(() => {
        if (!cancelled) setGroups([]);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  function view(doc: DocumentSummary) {
    setParams({ documento: doc.id });
  }

  return (
    <>
      <StepNav current={2} processId={id} />
      <h1>Etapa 2 · Documentos</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}

      <UploadDropzone processId={id} onUploaded={reload} />
      <DocumentList
        documents={documents}
        processId={id}
        onView={view}
        onCreateActivity={setCreating}
        onChanged={reload}
      />
      {polling && <p className="muted">Há documentos em processamento; a lista é atualizada sozinha.</p>}

      {detail && detail.id === viewId && (
        <Modal title={detail.original_name} onClose={() => setParams({})}>
          <DocumentViewer doc={detail} />
        </Modal>
      )}

      {creating && (
        <Modal title="Criar atividade a partir do documento" onClose={() => setCreating(null)}>
          <ActivityFromDocument
            key={creating.id}
            processId={id}
            doc={creating}
            groups={groups}
            onSaved={(text) => {
              setCreating(null);
              setMessage(text);
              reload();
            }}
            onCancel={() => setCreating(null)}
          />
        </Modal>
      )}

      <p>
        <Link to={`/processos/${id}/atividades`}>Ir para a Etapa 3 · Atividades</Link>
      </p>
    </>
  );
}
