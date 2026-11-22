import { useEffect, useState, type ReactNode } from "react";
import { useParams } from "react-router";
import { errorMessage, request } from "../api/client";
import type { Activity, Process, TableChoice } from "../api/types";
import { ComprovanteLayoutEditor } from "../components/ComprovanteLayoutEditor";
import { GeneratedBlock } from "../components/GeneratedBlock";
import { ReportDraftEditor } from "../components/ReportDraftEditor";
import { StepNav } from "../components/StepNav";
import { GENERATION_CODE_LABELS, STATUS_LABELS } from "../labels";

/** The editor of a block opens on demand: it loads its own data only when the user asks for it. */
function Disclosure({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="disclosure">
      <button
        type="button"
        className="btn btn-secondary"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {label}
      </button>
      {open && <div className="disclosure-body">{children}</div>}
    </div>
  );
}

/** UIG-06: the activities that do not go in a document: pending review, or validated without group and item. */
function leftOutCount(activities: Activity[]): number {
  return activities.filter(
    (a) =>
      a.status === "AGUARDANDO_REVISAO" ||
      (a.status === "VALIDADA" && (a.group_number === null || a.item_number === null)),
  ).length;
}

/**
 * Etapa 5: the three generated documents, the draft of the report inside the Relatório and the arrangement
 * inside the Comprovante. The dossier checklist and the conclusion of the process are in the Etapa 7. In a concluded or archived process the
 * draft and the arrangement are read only; in a concluded one the Comprovante cannot be generated, since
 * its originals are gone, while every version already generated can still be downloaded (DEL-13).
 */
export function ProcessGenerated() {
  const { id = "" } = useParams();
  const [process, setProcess] = useState<Process | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [chosenTableVersionId, setChosenTableVersionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    request<Process>("GET", `/api/processes/${id}`)
      .then((found) => {
        if (!cancelled) setProcess(found);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    request<Activity[]>("GET", `/api/processes/${id}/activities`)
      .then((found) => {
        if (!cancelled) setActivities(found);
      })
      .catch(() => {
        if (!cancelled) setActivities([]);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    request<TableChoice>("GET", `/api/processes/${id}/scoring/table`)
      .then((found) => {
        if (!cancelled) setChosenTableVersionId(found.chosen?.version.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setChosenTableVersionId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const readOnly = process !== null && (process.status === "CONCLUIDO" || process.status === "ARQUIVADO");
  const concluded = process?.status === "CONCLUIDO";
  const leftOut = leftOutCount(activities);

  return (
    <>
      <StepNav current={5} processId={id} />
      <h1>Etapa 5 · Documentos gerados</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {process && readOnly && (
        <p className="review-summary">
          Processo {STATUS_LABELS[process.status].toLowerCase()}: o rascunho do Relatório e o arranjo do Comprovante só
          podem ser lidos.
        </p>
      )}
      {process && (
        <>
          <GeneratedBlock processId={id} kind="TABELA" leftOut={leftOut} chosenTableVersionId={chosenTableVersionId} />
          <GeneratedBlock processId={id} kind="RELATORIO" leftOut={leftOut}>
            <Disclosure label="Revisar rascunho do Relatório">
              <ReportDraftEditor processId={id} readOnly={readOnly} />
            </Disclosure>
          </GeneratedBlock>
          <GeneratedBlock
            processId={id}
            kind="COMPROVANTE"
            leftOut={leftOut}
            disabledReason={concluded ? GENERATION_CODE_LABELS.ORIGINAIS_EXCLUIDOS : undefined}
          >
            <Disclosure label="Revisar arranjo do Comprovante">
              <ComprovanteLayoutEditor processId={id} readOnly={readOnly} />
            </Disclosure>
          </GeneratedBlock>
        </>
      )}
    </>
  );
}
