import { useEffect, useEffectEvent } from "react";

/** TELA-03, UIG-04, UIG-08: how often a screen asks the server again while something runs. */
export const POLL_INTERVAL_MS = 3000;

/**
 * Calls `tick` every `intervalMs` while `active` is true; it stops when `active` turns false and
 * when the component unmounts. `tick` may change on every render: the clock does not restart.
 */
export function usePolling(tick: () => void, active: boolean, intervalMs: number = POLL_INTERVAL_MS): void {
  const run = useEffectEvent(tick);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(run, intervalMs);
    return () => clearInterval(timer);
  }, [active, intervalMs]);
}
