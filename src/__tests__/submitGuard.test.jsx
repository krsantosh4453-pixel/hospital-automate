import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"

import { useSubmitGuard } from "../utils/submitGuard.js"

// RL-04: a double click on a money form must send one request, not two.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root

afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

function renderForm(handler, options) {
  function Form() {
    const [onSubmit, submitting] = useSubmitGuard(handler, options)
    return (
      <form onSubmit={onSubmit}>
        <button type="submit" disabled={submitting}>{submitting ? "Saving" : "Save"}</button>
      </form>
    )
  }
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<Form />))
  return host.querySelector("form")
}

const submit = (form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))

describe("useSubmitGuard", () => {
  it("runs the handler once when the form is submitted twice before it finishes", async () => {
    let finish
    const handler = vi.fn(() => new Promise((resolve) => { finish = resolve }))
    const form = renderForm(handler)

    act(() => { submit(form); submit(form) })

    expect(handler).toHaveBeenCalledTimes(1)
    expect(host.querySelector("button").disabled).toBe(true)
    await act(async () => finish())
    expect(host.querySelector("button").disabled).toBe(false)
  })

  it("reports a failure and allows the next submit", async () => {
    const handler = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce()
    const onError = vi.fn()
    const form = renderForm(handler, { onError })

    await act(async () => { submit(form) })
    await act(async () => { submit(form) })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: "offline" }))
    expect(handler).toHaveBeenCalledTimes(2)
  })

  it("prevents the browser's own form submission", () => {
    const form = renderForm(vi.fn().mockResolvedValue())
    const event = new Event("submit", { bubbles: true, cancelable: true })

    act(() => { form.dispatchEvent(event) })

    expect(event.defaultPrevented).toBe(true)
  })
})
