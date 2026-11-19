import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

// The loader caches per module instance, so each test gets fresh modules.
async function setup({ stored, onHindiModuleLoaded }) {
  vi.resetModules()
  vi.doUnmock("../assets/i18n/hiPages.js")
  if (onHindiModuleLoaded) {
    vi.doMock("../assets/i18n/hiPages.js", () => {
      onHindiModuleLoaded()
      return { default: { Radiology: "रेडियोलॉजी" } }
    })
  }
  if (stored) localStorage.setItem("hms_language", stored)
  const loader = await import("../assets/i18n/loadHindiPages.js")
  const { LanguageProvider } = await import("../assets/context/LanguageProvider.jsx")
  const { useLanguage } = await import("../assets/context/LanguageContext.jsx")

  function Probe() {
    const { t, setLanguage } = useLanguage()
    return (
      <>
        <p data-shell>{t("Logout")}</p>
        <p data-page>{t("Radiology")}</p>
        <button onClick={() => setLanguage("hi")}>hi</button>
      </>
    )
  }

  const host = document.createElement("div")
  document.body.appendChild(host)
  const root = createRoot(host)
  await act(async () => root.render(<LanguageProvider><Probe /></LanguageProvider>))
  return { host, root, loader }
}

const text = (host, attr) => host.querySelector(`[${attr}]`).textContent

describe("Hindi page dictionary loading", () => {
  let mounted

  afterEach(() => {
    act(() => mounted.root.unmount())
    mounted.host.remove()
    localStorage.removeItem("hms_language")
  })

  it("never loads the Hindi dictionary for English users", async () => {
    const hindiModuleLoaded = vi.fn()
    mounted = await setup({ stored: null, onHindiModuleLoaded: hindiModuleLoaded })

    expect(text(mounted.host, "data-shell")).toBe("Logout")
    expect(text(mounted.host, "data-page")).toBe("Radiology")
    expect(hindiModuleLoaded).not.toHaveBeenCalled()
    expect(mounted.loader.getLoadedHindiPages()).toBeNull()
  })

  it("loads page text when the user switches to Hindi", async () => {
    mounted = await setup({ stored: null })

    await act(async () => mounted.host.querySelector("button").click())
    await act(() => mounted.loader.loadHindiPages())

    expect(text(mounted.host, "data-shell")).toBe("लॉग आउट")
    expect(text(mounted.host, "data-page")).toBe("रेडियोलॉजी")
  })

  it("loads page text on start when Hindi was the saved choice", async () => {
    mounted = await setup({ stored: "hi" })
    await act(() => mounted.loader.loadHindiPages())

    expect(text(mounted.host, "data-shell")).toBe("लॉग आउट")
    expect(text(mounted.host, "data-page")).toBe("रेडियोलॉजी")
  })
})
