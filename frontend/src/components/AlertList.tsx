import type { Alert } from "../api/types";
import { ALERT_CODE_LABELS, SEVERITIES, SEVERITY_LABELS } from "../labels";
import { NormLink } from "./NormLink";

/** UI-03, NLINK-03: alerts grouped by severity, each with its norm reference and, when the rule cites a registered norm, the norm. */
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
                  <strong>{ALERT_CODE_LABELS[a.code] ?? a.code}</strong>: {a.message}
                  <br />
                  <small>Referência normativa: {a.norm_reference}</small>
                  {a.norm_title && (
                    <>
                      <br />
                      <small>
                        Norma:{" "}
                        <NormLink
                          title={a.norm_title}
                          url={a.norm_url ?? null}
                          fileUrl={a.norm_file_url ?? null}
                          archived={a.norm_archived ?? false}
                        />
                      </small>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}
