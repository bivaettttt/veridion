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

test("create a workspace, import two versions and compare them", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Fill local demo credentials" })
    .click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Create project", { exact: true }).first().click();
  const projectName = `Browser integration ${Date.now()}`;
  await page.getByLabel("Project name").fill(projectName);
  await page
    .getByLabel("Description")
    .fill("Exercise the import worker with isolated synthetic documents.");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: projectName })).toBeVisible();

  async function upload(text: string) {
    await page.getByRole("link", { name: "Sources", exact: true }).click();
    await page
      .getByText("Upload source or add a version", { exact: true })
      .click();
    await page
      .getByLabel("Source title")
      .fill("Browser integration specification");
    await page.getByLabel("Original file").setInputFiles({
      name: "specification.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(text),
    });
    await page.getByRole("button", { name: "Queue import" }).click();
    await page.getByRole("link", { name: "Monitor processing" }).click();
  }

  await upload("Build 1.4 documents a REST integration interface.");
  await expect(page.getByText("done", { exact: true })).toHaveCount(1, {
    timeout: 45_000,
  });
  await upload("Build 2.0 documents a webhook integration interface.");
  await expect(page.getByText("done", { exact: true })).toHaveCount(2, {
    timeout: 45_000,
  });

  await page.getByRole("link", { name: "Research desk", exact: true }).click();
  await page
    .getByLabel("Research question")
    .fill("What webhook integration interface is documented?");
  await page.getByRole("button", { name: "Search sources" }).click();
  await expect(
    page.getByText("Build 2.0 documents a webhook integration interface.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: "Browser integration specification",
      exact: true,
    })
    .click();
  await page.getByLabel("Compare with").selectOption("1");
  await expect(
    page.getByText("Build 1.4 documents a REST integration interface.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("compare conflicting evidence, submit review, export a report and run the lab", async ({
  page,
}) => {
  test.setTimeout(120_000);
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
  await page
    .getByLabel("Research question")
    .fill("What availability was measured in build 2.0?");
  await page.getByRole("button", { name: "Run analysis" }).click();
  await expect(page.getByText("Mixed evidence", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Open full research record" }).click();
  await expect(
    page.getByText("Potential conflict", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByLabel("Rationale", { exact: true })
    .fill("The East and West observations differ under the same profile.");
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByText("In review", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Report title").fill("Availability comparison");
  await page
    .getByLabel("Research notes")
    .fill("Confirm the measurement method before publishing the result.");
  await page.getByRole("button", { name: "Save report snapshot" }).click();
  await expect(
    page.getByRole("heading", { name: "Availability comparison" }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download Markdown" }).click();
  expect((await download).suggestedFilename()).toBe("veridion-snapshot-1.md");
  await page
    .getByLabel("Notes for next snapshot")
    .fill("Review the test profiles in the next meeting.");
  await page.getByRole("button", { name: "Save new snapshot" }).click();
  await page.getByLabel("Compare with").selectOption("1");
  await expect(
    page.getByText(
      "Confirm the measurement method before publishing the result.",
      { exact: true },
    ),
  ).toBeVisible();

  await page.getByRole("link", { name: "Evaluation", exact: true }).click();
  await page.getByRole("button", { name: "Run evaluation" }).click();
  await expect(
    page.getByRole("heading", { name: "Evaluation results" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Veridion Lab", exact: true }).click();
  const labResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && response.url().endsWith("/lab"),
  );
  await page.getByRole("button", { name: "Run scenarios" }).click();
  expect((await labResponse).status()).toBe(201);
  await expect(page.getByText("24 of 24 passed", { exact: true })).toBeVisible({
    timeout: 45_000,
  });
});
