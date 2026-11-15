import { expect, test } from "@playwright/test";

test("trace a research conclusion to the exact source passage", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Fill local demo credentials" })
    .click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await page
    .getByRole("link", { name: /Northstar Research/ })
    .first()
    .click();
  await page.getByRole("link", { name: "Open research desk" }).click();
  await page.getByRole("button", { name: "Run analysis" }).click();
  await expect(
    page.getByRole("heading", { name: /target remains unverified/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Citation inspector" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Exact text, range and run context verified.",
  );
  if (process.env.VERIDION_SCREENSHOT) {
    await page.getByRole("heading", { name: "Research desk" }).click();
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: process.env.VERIDION_SCREENSHOT });
  }
  await page.getByRole("link", { name: "Open source" }).click();
  await expect(page.locator("mark")).toContainText("2 000 concurrent users");
});
