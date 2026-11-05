import { expect, test } from "@playwright/test"
import { signInAs, uniqueName } from "./helpers.js"

test("store adds a supplier and an item, raises a purchase order and receives it into stock", async ({ page }) => {
  const supplier = uniqueName("E2E Supplier")
  const item = uniqueName("E2E Gauze")
  const reference = uniqueName("PO").replace(" ", "-")

  await signInAs(page, "demo.inventory")
  await page.goto("/inventory")

  // Supplier
  await page.getByRole("tab", { name: "Suppliers" }).click()
  await page.getByRole("button", { name: "Add supplier" }).first().click()
  await page.getByRole("dialog").getByLabel("Supplier name").fill(supplier)
  await page.getByRole("dialog").getByRole("button", { name: "Add supplier" }).click()
  await expect(page.getByRole("cell", { name: supplier, exact: true })).toBeVisible()

  // Item with its own unit, reorder level and usual supplier: 5 boxes is below 25, so low stock.
  await page.getByRole("tab", { name: "Stock" }).click()
  await page.getByRole("button", { name: "Add item" }).first().click()
  const itemForm = page.getByRole("dialog")
  await itemForm.getByLabel("Item name").fill(item)
  await itemForm.getByLabel("Category").selectOption("Surgical")
  await itemForm.getByLabel("Quantity in stock").fill("5")
  await itemForm.getByLabel("Unit").fill("Box")
  await itemForm.getByLabel("Reorder level").fill("25")
  await itemForm.getByLabel("Usual supplier").selectOption({ label: supplier })
  await itemForm.getByLabel("Expiry (month)").fill("2028-06")
  await itemForm.getByRole("button", { name: "Add item" }).click()
  const stockRow = page.getByRole("row").filter({ hasText: item })
  await expect(stockRow).toContainText("5 Box")
  await expect(stockRow).toContainText("Low Stock")

  // Purchase order for 40 boxes
  await page.getByRole("tab", { name: "Purchase orders" }).click()
  await page.getByRole("button", { name: "New purchase order" }).first().click()
  const orderForm = page.getByRole("dialog")
  await orderForm.getByLabel(/^Supplier/).selectOption({ label: supplier })
  await orderForm.getByLabel("Order reference").fill(reference)
  await orderForm.getByLabel("Item 1", { exact: true }).selectOption({ label: item })
  await orderForm.getByLabel("Qty", { exact: true }).fill("40")
  await orderForm.getByLabel("Unit cost (₹)").fill("120")
  await orderForm.getByRole("button", { name: "Raise order" }).click()
  const orderRow = page.getByRole("row").filter({ hasText: reference })
  await expect(orderRow).toContainText("0/40")
  await expect(orderRow).toContainText("Ordered")

  // Receive all 40 against the supplier's invoice
  await orderRow.getByRole("button", { name: "Receive" }).click()
  const receiptForm = page.getByRole("dialog")
  await receiptForm.getByLabel("Supplier invoice / delivery note no.").fill(`INV-${reference}`)
  await receiptForm.getByLabel("Batch").fill("E2E-B1")
  await receiptForm.getByRole("button", { name: "Record receipt" }).click()
  await expect(orderRow).toContainText("40/40")
  await expect(orderRow).toContainText("Received")

  // Stock is now 45 boxes and no longer low
  await page.getByRole("tab", { name: "Stock" }).click()
  await expect(stockRow).toContainText("45 Box")
  await expect(stockRow).toContainText("In Stock")
})

test("pharmacist sees purchase orders but cannot change them", async ({ page }) => {
  await signInAs(page, "demo.pharmacist")
  await page.goto("/inventory")
  await page.getByRole("tab", { name: "Purchase orders" }).click()

  await expect(page.getByRole("button", { name: "New purchase order" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Receive" })).toHaveCount(0)
})

test("requisition is approved, ordered, received, issued to a ward and partly returned", async ({ browser }) => {
  test.setTimeout(120000)
  const supplier = uniqueName("E2E Req Supplier")
  const item = uniqueName("E2E Saline")
  const store = await (await browser.newContext()).newPage()
  await signInAs(store, "demo.inventory")
  await store.goto("/inventory")
  await store.getByRole("tab", { name: "Suppliers" }).click()
  await store.getByRole("button", { name: "Add supplier" }).first().click()
  await store.getByRole("dialog").getByLabel("Supplier name").fill(supplier)
  await store.getByRole("dialog").getByRole("button", { name: "Add supplier" }).click()
  await store.getByRole("tab", { name: "Stock" }).click()
  await store.getByRole("button", { name: "Add item" }).first().click()
  const itemForm = store.getByRole("dialog")
  await itemForm.getByLabel("Item name").fill(item)
  await itemForm.getByLabel("Category").selectOption("Surgical")
  await itemForm.getByLabel("Quantity in stock").fill("1")
  await itemForm.getByLabel("Expiry (month)").fill("2028-06")
  await itemForm.getByRole("button", { name: "Add item" }).click()
  const stockRow = store.getByRole("row").filter({ hasText: item })
  await expect(stockRow).toBeVisible()

  // The pharmacy asks for 30.
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/inventory")
  await pharmacist.getByRole("tab", { name: "Requisitions" }).click()
  await pharmacist.getByRole("button", { name: "New requisition" }).click()
  const reqForm = pharmacist.getByRole("dialog")
  await reqForm.getByRole("combobox", { name: "Item" }).selectOption({ label: item })
  await reqForm.getByRole("spinbutton", { name: "Quantity" }).fill("30")
  await reqForm.getByRole("button", { name: "Raise requisition" }).click()
  const pharmacistRow = pharmacist.getByRole("row").filter({ hasText: item })
  await expect(pharmacistRow).toContainText("Submitted")
  await expect(pharmacistRow.getByRole("button", { name: "Approve" })).toHaveCount(0)

  // The manager approves it.
  const manager = await (await browser.newContext()).newPage()
  await signInAs(manager, "demo.manager")
  await manager.goto("/inventory")
  await manager.getByRole("tab", { name: "Requisitions" }).click()
  const managerRow = manager.getByRole("row").filter({ hasText: item })
  await managerRow.getByRole("button", { name: "Approve" }).click()
  await expect(managerRow).toContainText("Approved")

  // The store orders it from the supplier.
  await store.getByRole("tab", { name: "Requisitions" }).click()
  const storeRow = store.getByRole("row").filter({ hasText: item })
  await storeRow.getByRole("button", { name: "Order" }).click()
  const orderForm = store.getByRole("dialog")
  await orderForm.getByLabel(/^Supplier/).selectOption({ label: supplier })
  await orderForm.getByLabel(/unit cost/).fill("25")
  await orderForm.getByRole("button", { name: "Place purchase order" }).click()
  await expect(storeRow).toContainText("Ordered")

  // Received in full.
  await store.getByRole("tab", { name: "Purchase orders" }).click()
  const orderRow = store.getByRole("row").filter({ hasText: item })
  await orderRow.getByRole("button", { name: "Receive" }).click()
  const receiptForm = store.getByRole("dialog")
  await receiptForm.getByLabel("Supplier invoice / delivery note no.").fill(uniqueName("INV").replace(" ", "-"))
  await receiptForm.getByRole("button", { name: "Record receipt" }).click()
  await expect(orderRow).toContainText("30/30")

  // 10 to a ward, 5 damaged back to the supplier.
  await store.getByRole("tab", { name: "Issues & returns" }).click()
  await store.getByLabel(/^Department/).selectOption({ index: 1 })
  // Options read "name · batch · stock", so pick ours by its value.
  const itemSelect = store.getByRole("combobox", { name: /^Item/ })
  await itemSelect.selectOption(await itemSelect.locator("option", { hasText: item }).getAttribute("value"))
  await store.getByRole("spinbutton", { name: /^Quantity/ }).fill("10")
  await store.getByRole("button", { name: "Issue", exact: true }).click()
  await expect(store.getByRole("row").filter({ hasText: item }).first()).toContainText("10")

  const openLine = store.getByRole("row").filter({ hasText: item }).filter({ hasText: "/ 30" })
  await openLine.getByRole("button", { name: "Return to supplier" }).click()
  const returnForm = store.getByRole("dialog")
  await returnForm.getByLabel(/^Quantity/).fill("5")
  await returnForm.getByLabel(/^Reason/).fill("Damaged packs")
  await returnForm.getByRole("button", { name: "Save" }).click()
  await expect(openLine).toContainText("25 / 30")

  await store.getByRole("tab", { name: "Stock" }).click()
  await expect(stockRow).toContainText("16")
})
