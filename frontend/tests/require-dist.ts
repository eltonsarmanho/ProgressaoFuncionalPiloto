/**
 * Whether `REQUIRE_DIST` asks for the bundle scan to fail, not skip, without `frontend/dist`.
 * Unset, empty, `0` and `false` (any case, with spaces) mean "not required": `Boolean("0")` is
 * true in JavaScript, so the raw variable cannot be used (TER-11).
 */
export function isDistRequired(value: string | undefined): boolean {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized !== "" && normalized !== "0" && normalized !== "false";
}
