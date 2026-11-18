import type { Alert } from "../api/types";
import { SEVERITIES, SEVERITY_LABELS } from "../labels";

/** UI-03: alerts grouped by severity, each with its norm reference. */
export function AlertList({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) return <p>Nenhum alerta de verificação.</p>;
  return (
    <>
      {SEVERITIES.map((severity) => {
        const group = alerts.filter((a) => a.severity === severity);
        if (group.length === 0) return null;
        const title = `${SEVERITY_LABELS[severity]} (${group.length})`;
        const headingId = `alerts-${severity}`;
        return (
          <section key={severity} aria-labelledby={headingId} className={`alert-group sev-${severity}`}>
            <h3 id={headingId}>{title}</h3>
            <ul>
              {group.map((a, i) => (
                <li key={`${a.code}-${i}`}>
                  <strong>{a.code}</strong>: {a.message}
                  <br />
                  <small>Referência normativa: {a.norm_reference}</small>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}
