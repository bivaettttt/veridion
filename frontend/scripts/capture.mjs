import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const root = process.env.VERIDION_WEB_URL || "http://127.0.0.1:3817";
const dir = new URL("../../assets/screenshots/", import.meta.url);
await mkdir(dir, { recursive: true });
const browser = await chromium.launch();
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    baseURL: root,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(60_000);
  const request = context.request;
  const api = async (path, data, form) => {
    const response = await request.fetch("/api/v1" + path, {
      method: data || form ? "POST" : "GET",
      data,
      form,
      headers: { "X-Veridion-Client": "1" },
      timeout: 150_000,
    });
    if (!response.ok()) throw new Error(path + ": " + (await response.text()));
    return response.json();
  };
  await api("/auth/login", {
    email: "researcher@northstar.test",
    password: "northstar-workspace",
  });
  const project = (await api("/projects")).find((row) => row.lab);
  const base = "/projects/" + project.id;
  const send = (question, provider = "extractive") =>
    api(base + "/answers", { query: question, provider });
  const availability = await send(
    "What availability was measured in build 2.0?",
  );
  const result = await send(
    "Does the platform support 10 000 concurrent users?",
  );
  if (result.output.assessment !== "INSUFFICIENT_EVIDENCE")
    throw new Error("Expected a capacity evidence gap");
  const run = await api(base + "/reports", {
    answer_id: result.id,
    title: "Northstar capacity assessment",
    notes:
      "The performance test covers sustained concurrency at 2,000 users under the steady profile.",
  });
  await api(base + "/answers/" + result.id + "/reviews", {
    decision: "IN_REVIEW",
    revision: 0,
    rationale: "Review the 10,000-user target and check the test conditions.",
  });
  await api(base + "/reports/" + run.id + "/snapshots", undefined, {
    notes:
      "Follow-up requested: run a workload at the target under the same conditions.",
  });
  await api(base + "/evaluations", {});
  if (!(await api(base + "/lab")).length) await api(base + "/lab", {});

  async function open(path, text) {
    await page.goto(base + path, { waitUntil: "domcontentloaded" });
    await page
      .getByRole("heading", { name: text, exact: true })
      .first()
      .waitFor();
  }
  async function image(name) {
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: fileURLToPath(new URL(name + ".png", dir)),
      animations: "disabled",
    });
    console.log(name);
  }
  await open("", "Northstar Research");
  await page.getByRole("heading", { name: "Recent research" }).waitFor();
  await page
    .getByText("saved answers in the current view", { exact: false })
    .waitFor();
  await image("overview");
  await open("/sources", "Source library");
  await page.getByRole("link", { name: "Platform specification" }).waitFor();
  await image("source-library");
  await page.getByRole("link", { name: "Platform specification" }).click();
  await page
    .getByText(
      "Build 2.0 documents a REST and webhook integration interface.",
      { exact: false },
    )
    .waitFor();
  await image("document-viewer");
  await page.getByLabel("Compare with").selectOption("1");
  await page
    .getByText("Build 1.4 documents a REST integration interface.", {
      exact: false,
    })
    .waitFor();
  await image("version-comparison");
  await open("/research", "Research desk");
  await image("search-workspace");
  await page.getByRole("button", { name: "Search sources" }).click();
  await page.getByRole("heading", { name: /Retrieved passages/ }).waitFor();
  await image("hybrid-search");
  await page.getByRole("button", { name: "Run analysis" }).click();
  await page
    .getByRole("heading", { name: /target remains unverified/ })
    .waitFor();
  await image("research-desk");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await page
    .getByRole("status")
    .filter({ hasText: /Exact text/ })
    .waitFor();
  await image("citation-inspector");
  await open("/answers/" + result.id, "Answer details");
  await page
    .getByRole("heading", { name: /target remains unverified/ })
    .waitFor();
  await image("claim-assessment");
  await open("/contradictions", "Contradiction explorer");
  await page
    .getByRole("button", { name: availability.query, exact: true })
    .first()
    .click();
  await page
    .getByText("Different values or polarity under matching conditions", {
      exact: true,
    })
    .first()
    .waitFor();
  await page
    .getByRole("heading", { name: "Evidence comparisons" })
    .scrollIntoViewIfNeeded();
  await image("contradiction-explorer");
  await open("/answers/" + result.id, "Answer details");
  await page
    .getByRole("heading", { name: "Human review" })
    .scrollIntoViewIfNeeded();
  await image("human-review");
  await open("/reports/" + run.id, "Northstar capacity assessment");
  await page.getByRole("button", { name: "Save new snapshot" }).waitFor();
  await image("report-editor");
  await page.getByLabel("Compare with").selectOption("1");
  await page.getByText("Snapshot 1 ·", { exact: false }).first().waitFor();
  await image("snapshot-comparison");
  await open("/evaluation", "Evaluation");
  await page.getByRole("heading", { name: "Evaluation results" }).waitFor();
  await image("evaluation");
  await open("/lab", "Veridion Lab");
  await page.getByRole("heading", { name: "Scenario results" }).waitFor();
  await image("lab");
} finally {
  await browser.close();
}
