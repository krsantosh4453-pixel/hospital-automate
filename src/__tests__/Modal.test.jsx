import React, { act, useState } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it } from "vitest"
import { Modal } from "../components/ui/Modal.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

// Pages pass onClose inline, so it is a new function on every render.
function Page() {
  const [name, setName] = useState("")
  return (
    <Modal open title="Add doctor" onClose={() => {}}>
      <input aria-label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
    </Modal>
  )
}

const typeInto = (input, text) => {
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set
  for (const ch of text) {
    act(() => {
      setValue.call(input, input.value + ch)
      input.dispatchEvent(new Event("input", { bubbles: true }))
    })
  }
}

describe("Modal", () => {
  let root
  let host

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  const render = () => {
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(<Page />))
    return document.querySelector('input[aria-label="Full name"]')
  }

  it("starts in the first form field", () => {
    const input = render()
    expect(document.activeElement).toBe(input)
  })

  it("keeps focus in the field while typing, even though onClose changes every render", () => {
    const input = render()
    typeInto(input, "Shivam")
    expect(input.value).toBe("Shivam")
    expect(document.activeElement).toBe(input)
  })
})
