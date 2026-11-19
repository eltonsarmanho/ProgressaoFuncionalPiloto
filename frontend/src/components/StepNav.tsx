import { Link } from "react-router";

const TOTAL_STEPS = 9;

const STEP_TITLES: Record<number, string> = {
  1: "Processo e interstício",
  2: "Documentos",
  3: "Atividades",
  4: "Pontuação",
  5: "Documentos gerados",
};

function stepPath(step: number, processId?: string): string | null {
  if (!processId) return null;
  if (step === 1) return `/processos/${processId}`;
  if (step === 2) return `/processos/${processId}/documentos`;
  if (step === 3) return `/processos/${processId}/atividades`;
  if (step === 4) return `/processos/${processId}/pontuacao`;
  if (step === 5) return `/processos/${processId}/gerados`;
  return null;
}

/** UI-04 / TELA-01: nine steps; only the enabled ones (default: step 1) are available. */
export function StepNav({
  enabled = [1, 2, 3, 4, 5],
  current = 1,
  processId,
  blocked,
}: {
  enabled?: number[];
  current?: number;
  processId?: string;
  /** SEC-05: the steps after `step` are closed (no link, `aria-disabled`) and `message` says why. */
  blocked?: { step: number; message: string };
}) {
  return (
    <nav aria-label="Etapas do processo">
      <ol className="steps">
        {Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map((n) => {
          if (!enabled.includes(n)) {
            return (
              <li key={n} className="step disabled" aria-disabled="true">
                Etapa {n} <small>em breve</small>
              </li>
            );
          }
          const label = `Etapa ${n} · ${STEP_TITLES[n] ?? ""}`;
          if (blocked && n > blocked.step) {
            return (
              <li key={n} className="step disabled" aria-disabled="true">
                {label}
              </li>
            );
          }
          const to = stepPath(n, processId);
          const content = to ? <Link to={to}>{label}</Link> : label;
          return n === current ? (
            <li key={n} className="step active" aria-current="step">
              {content}
            </li>
          ) : (
            <li key={n} className="step">
              {content}
            </li>
          );
        })}
      </ol>
      {blocked && (
        <p className="step-blocked" aria-live="polite">
          {blocked.message}
        </p>
      )}
    </nav>
  );
}
