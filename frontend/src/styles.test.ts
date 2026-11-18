import { describe, expect, it } from "vitest";
import css from "./styles.css?raw";
import html from "../index.html?raw";

const PX_PER_REM = 16;

function toPx(value: string, unit: string): number {
  const n = Number(value);
  return unit === "px" ? n : n * PX_PER_REM;
}

describe("UI-06: utilizável em 360 px sem rolagem horizontal", () => {
  it("não declara largura fixa ou mínima acima de 360 px", () => {
    const fixed = [
      ...css.matchAll(/(?:^|[\s;{])(width|min-width|flex-basis)\s*:\s*([\d.]+)(px|rem|em)/g),
    ].map((m) => ({ prop: m[1], px: toPx(m[2], m[3]) }));
    const gridMins = [...css.matchAll(/minmax\(\s*([\d.]+)(px|rem|em)/g)].map((m) => ({
      prop: "minmax",
      px: toPx(m[1], m[2]),
    }));
    const tooWide = [...fixed, ...gridMins].filter((d) => d.px > 360);
    expect(tooWide).toEqual([]);
  });

  it("usa contêineres fluidos e a meta viewport de dispositivo", () => {
    expect(css).toMatch(/\.container\s*{[^}]*width:\s*100%/);
    expect(html).toContain('name="viewport" content="width=device-width, initial-scale=1.0"');
  });
});
