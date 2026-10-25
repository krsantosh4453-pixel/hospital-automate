// @vitest-environment node
// Pages call the backend only through src/services/api.js. A call to a
// method that does not exist there fails at runtime (TypeError) the first
// time a user reaches that screen, so check every call site statically.
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import api from "../services/api.js"

const SRC = fileURLToPath(new URL("..", import.meta.url))

function sourceFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return name === "__tests__" ? [] : sourceFiles(path)
    return /\.(js|jsx)$/.test(name) ? [path] : []
  })
}

describe("api client usage", () => {
  it("every api.<group>.<method> used by the app exists", () => {
    const missing = new Set()
    for (const file of sourceFiles(SRC)) {
      if (file.endsWith(join("services", "api.js"))) continue
      const src = readFileSync(file, "utf8")
      for (const [, group, method] of src.matchAll(/\bapi\.([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(/g)) {
        if (typeof api[group]?.[method] !== "function") {
          missing.add(`${relative(SRC, file)}: api.${group}.${method}`)
        }
      }
    }
    expect([...missing]).toEqual([])
  })
})
