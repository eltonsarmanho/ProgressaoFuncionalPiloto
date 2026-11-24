/** How many rows of the scoring are not scored: they wait for "Validar" or have no points. */
export function countUnscored(rows: { status: string }[]): number {
  return rows.filter((r) => r.status !== "PONTUADA").length;
}
