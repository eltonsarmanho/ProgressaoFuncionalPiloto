import { describe, expect, expectTypeOf, it } from "vitest";
import type { Criterion, ScoringResult, ScoringRow } from "./types";

/** TELA-01 / TELA-02: the scoring API contract carries the group I PIT hours (checked by `tsc -b`). */
describe("tipos da API de pontuação", () => {
  it("TELA-01: a linha traz pit_hours (texto decimal ou nulo fora do Grupo I)", () => {
    expectTypeOf<ScoringRow["pit_hours"]>().toEqualTypeOf<string | null>();
    const row: Pick<ScoringRow, "pit_hours" | "points"> = { pit_hours: "8.00", points: "0.00" };
    expect(row.pit_hours).toBe("8.00");
  });

  it("TELA-01: o resultado traz as horas do Grupo I por período letivo e o total de horas", () => {
    expectTypeOf<ScoringResult["group1_hours_by_period"]>().toEqualTypeOf<Record<string, string>>();
    expectTypeOf<ScoringResult["group1_total_hours"]>().toEqualTypeOf<string>();
    const sample: Pick<ScoringResult, "group1_hours_by_period" | "group1_total_hours"> = {
      group1_hours_by_period: { "2023.1": "12.00", "2023.2": "12.00" },
      group1_total_hours: "24.00",
    };
    expect(sample.group1_total_hours).toBe("24.00");
  });

  it("OFI-06: o critério traz min_hours (texto decimal ou nulo)", () => {
    expectTypeOf<Criterion["min_hours"]>().toEqualTypeOf<string | null>();
    const minimum: Pick<Criterion, "min_hours"> = { min_hours: "20.00" };
    expect(minimum.min_hours).toBe("20.00");
  });
});
