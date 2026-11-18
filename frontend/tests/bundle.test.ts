// @vitest-environment node
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { isDistRequired } from "./require-dist";

/**
 * VER-07 / EXT-06: the production bundle must not carry the MariTalk key or its name.
 * `scripts/check_bundle_no_secrets.sh` holds the patterns; CI runs it after `npm run build`.
 */
const SCRIPT = resolve(import.meta.dirname, "../../scripts/check_bundle_no_secrets.sh");
const DIST = resolve(import.meta.dirname, "../dist");

// The Build gate builds first and sets REQUIRE_DIST=1: then a missing dist fails instead of skipping.
// REQUIRE_DIST=0 or false does not count as set (TER-11).
const REQUIRE_DIST = isDistRequired(process.env.REQUIRE_DIST);

const scan = (dir: string) => spawnSync("bash", [SCRIPT, dir], { encoding: "utf8" });

const created: string[] = [];
function bundleWith(content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "bundle-"));
  created.push(dir);
  writeFileSync(join(dir, "index.js"), content);
  return dir;
}
afterEach(() => created.splice(0).forEach((dir) => rmSync(dir, { recursive: true, force: true })));

describe("pacote de produção sem segredos", () => {
  it.skipIf(!REQUIRE_DIST && !existsSync(DIST))("o pacote em dist (npm run build) não contém MARITALK nem token de chave", () => {
    expect(existsSync(DIST), "frontend/dist não existe: rode npm run build antes (REQUIRE_DIST está definido)").toBe(true);
    const outcome = scan(DIST);
    expect(outcome.stderr).toBe("");
    expect(outcome.status).toBe(0);
  });

  it("um pacote limpo passa", () => {
    expect(scan(bundleWith("const a = fetch('/api/processes');")).status).toBe(0);
  });

  it.each([
    ["o nome MARITALK", "const k = process.env.MARITALK_API_KEY;"],
    ["o nome em minúsculas", "const base = 'maritalk';"],
    ["um cabeçalho Bearer com token", "headers: { Authorization: 'Bearer abcdefghijklmnopqrstuvwx' }"],
    ["um token com forma de chave", "const key = 'sk-abcdefghijklmnopqrstuv1234';"],
  ])("falha quando o pacote contém %s", (_name, content) => {
    expect(scan(bundleWith(content)).status).toBe(1);
  });

  it("falha quando o diretório do pacote não existe", () => {
    expect(scan(join(tmpdir(), "nao-existe-bundle")).status).toBe(2);
  });
});
