const TOTAL_STEPS = 9;

/** UI-04: nine steps, only step 1 available in this release. */
export function StepNav() {
  return (
    <nav aria-label="Etapas do processo">
      <ol className="steps">
        {Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map((n) =>
          n === 1 ? (
            <li key={n} className="step active" aria-current="step">
              Etapa 1 · Processo e interstício
            </li>
          ) : (
            <li key={n} className="step disabled" aria-disabled="true">
              Etapa {n} <small>em breve</small>
            </li>
          ),
        )}
      </ol>
    </nav>
  );
}
