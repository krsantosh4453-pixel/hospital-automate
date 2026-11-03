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
