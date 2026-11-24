// @vitest-environment node
import { describe, expect, it } from "vitest";
import { isDistRequired } from "./require-dist";

describe("TER-11: REQUIRE_DIST só vale quando pede a varredura obrigatória", () => {
  it.each(["1", "true", "TRUE", "yes", "  1  "])("o valor %j exige o pacote", (value) => {
    expect(isDistRequired(value)).toBe(true);
  });

  it.each([undefined, "", "   ", "0", " 0 ", "false", "FALSE", "False"])("o valor %j não exige o pacote", (value) => {
    expect(isDistRequired(value)).toBe(false);
  });
});
