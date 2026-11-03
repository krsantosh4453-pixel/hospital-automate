import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it } from "vitest"
import { LanguageProvider, useLanguage } from "../assets/context/LanguageContext.jsx"
import { Button, PageHeader, Select, TableWrap } from "../components/ui"
import HI_PAGES from "../assets/i18n/hiPages.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe("Hindi page text (A17)", () => {
  let root
  let host

  const render = (element) => {
    localStorage.setItem("hms_language", "hi")
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(<LanguageProvider>{element}</LanguageProvider>))
  }

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
    localStorage.removeItem("hms_language")
  })

  it("translates page titles, buttons and table headers, and keeps unknown text", () => {
    render(
      <>
        <PageHeader title="Radiology" description="Some text nobody translated" />
        <Button>Refresh</Button>
        <TableWrap><table><thead><tr><th>Patient</th><th>Accession</th></tr></thead></table></TableWrap>
      </>,
    )

    expect(host.querySelector("h1").textContent).toBe("रेडियोलॉजी")
    expect(host.textContent).toContain("Some text nobody translated")
    expect(host.querySelector("button").textContent).toBe("रीफ़्रेश करें")
    expect([...host.querySelectorAll("th")].map((th) => th.textContent)).toEqual(["मरीज़", "क्रमांक"])
  })

  it("fills names and numbers into translated sentences, in Hindi word order", () => {
    function Sentence() {
      const { t } = useLanguage()
      return (
        <>
          <p>{t("Signed in as {name}", { name: "Admin" })}</p>
          <p>{t("Nobody translated {count} things", { count: 3 })}</p>
        </>
      )
    }
    render(<Sentence />)

    const [signedIn, unknown] = host.querySelectorAll("p")
    expect(signedIn.textContent).toBe("Admin के रूप में साइन इन")
    expect(unknown.textContent).toBe("Nobody translated 3 things")
  })

  it("keeps every placeholder of the English sentence in its Hindi", () => {
    const names = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
    const broken = Object.entries(HI_PAGES).filter(([english, hindi]) =>
      !hindi.trim() || names(english).join() !== names(hindi).join())
    expect(broken).toEqual([])
  })

  it("never changes the value an option submits", () => {
    render(
      <Select defaultValue="Sick leave" aria-label="Type">
        <option>Sick leave</option>
        <option value="Fitness">Fitness</option>
      </Select>,
    )

    const [implicit, explicit] = host.querySelectorAll("option")
    expect([implicit.value, implicit.textContent]).toEqual(["Sick leave", "Sick leave"])
    expect([explicit.value, explicit.textContent]).toEqual(["Fitness", "फ़िटनेस"])
  })
})
