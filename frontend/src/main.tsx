import { useState, type FormEvent, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Database,
  FileText,
  FolderOpen,
  GitCompareArrows,
  Layers3,
  LogOut,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  FlaskConical,
} from "lucide-react";
import {
  ApiError,
  call,
  date,
  label,
  type Answer,
  type AnswerItem,
  type Citation,
  type Eval,
  type Hit,
  type Project,
  type Source,
  type User,
  type Version,
  type LabRun,
} from "./data";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-600.css";
import "@fontsource/dm-sans/latin-700.css";
import "@fontsource/instrument-serif/latin-400.css";
import "./style.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: 5000 } },
});
const EXAMPLE = "Does the platform support 10 000 concurrent users?";
const localPass = "northstar-workspace";

function Brand() {
  return (
    <div className="brand">
      <div className="symbol">
        <Layers3 size={22} />
      </div>
      <div>
        Veridion<small>Research workspace</small>
      </div>
    </div>
  );
}
function ErrorMessage({ error }: { error: unknown }) {
  return error ? (
    <p className="error" role="alert">
      <CircleAlert size={16} />
      {error instanceof Error ? error.message : String(error)}
    </p>
  ) : null;
}
function Badge({ value }: { value: string }) {
  const type = [
    "VALID",
    "SUPPORTED_BY_SOURCES",
    "VERIFIED",
    "DONE",
    "CURRENT",
  ].includes(value)
    ? "positive"
    : /INSUFFICIENT|MIXED|CONFLICT|IN_REVIEW|FAILED/.test(value)
      ? "caution"
      : "neutral";
  return <span className={"badge " + type}>{label(value)}</span>;
}
function Header({
  eyebrow,
  title,
  text,
  action,
}: {
  eyebrow: string;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <header className="heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {text && <p>{text}</p>}
      </div>
      {action}
    </header>
  );
}
function Login() {
  const local = useQueryClient();
  const [email, setEmail] = useState("researcher@northstar.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function signIn(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      await call("/auth/login", { email, password });
      await local.invalidateQueries({ queryKey: ["user"] });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <div className="login-aside">
        <Brand />
        <div>
          <span className="eyebrow">Evidence-based research</span>
          <h1>
            Trace every
            <br /> conclusion.
          </h1>
          <p>
            Consult versioned sources, inspect citations and record the
            reasoning behind research decisions.
          </p>
        </div>
      </div>
      <form className="login-form" onSubmit={signIn}>
        <h2>Sign in to Veridion</h2>
        <p>Open your research workspace.</p>
        <label>
          Email address
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
          <ArrowRight size={16} />
        </button>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setEmail("researcher@northstar.test");
            setPassword(localPass);
          }}
        >
          Fill local demo credentials
        </button>
        <ErrorMessage error={error} />
      </form>
    </div>
  );
}

const mainNav = [
  ["Overview", "", FolderOpen],
  ["Research desk", "research", Search],
  ["Sources", "sources", BookOpen],
  ["Ingestion", "ingestion", Database],
  ["Claims & review", "claims", ClipboardCheck],
  ["Contradictions", "contradictions", GitCompareArrows],
  ["Reports", "reports", FileText],
] as const;
const labNav = [
  ["Evaluation", "evaluation", SlidersHorizontal],
  ["Veridion Lab", "lab", FlaskConical],
] as const;
function Shell({ user }: { user: User }) {
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: () => call<Project[]>("/projects"),
  });
  const path = useLocation();
  const navigate = useNavigate();
  const local = useQueryClient();
  const pid = path.pathname.match(/^\/projects\/([^/]+)/)?.[1];
  const project = projects.data?.find((entry) => entry.id === pid);
  const base = project ? "/projects/" + project.id : "/";
  const links = (
    items: ReadonlyArray<readonly [string, string, typeof Search]>,
  ) =>
    items.map(([name, slug, Icon]) => (
      <NavLink end={!slug} key={name} to={slug ? base + "/" + slug : base}>
        <Icon size={17} />
        {name}
      </NavLink>
    ));
  return (
    <div className="layout">
      <aside className="sidebar">
        <Link className="brand-link" to="/">
          <Brand />
        </Link>
        <nav aria-label="Workspace">
          <Link className="project-link" to="/">
            <span className="project-icon">
              <FolderOpen size={16} />
            </span>
            <span>
              {project?.name ?? "Projects"}
              <small>{project ? "Change project" : "Project directory"}</small>
            </span>
            <ChevronRight size={15} />
          </Link>
          {project && (
            <>
              <div className="nav-label">Workspace</div>
              {links(mainNav)}
              {project.lab && (
                <>
                  <div className="nav-label">Validation</div>
                  {links(labNav)}
                </>
              )}
              {project.role === "ADMIN" && (
                <>
                  <div className="nav-label">Management</div>
                  {links([["Administration", "admin", ShieldCheck]])}
                </>
              )}
            </>
          )}
        </nav>
        <div className="sidebar-foot">
          <span className="avatar">
            {user.name
              .split(" ")
              .map((word) => word[0])
              .slice(0, 2)
              .join("")}
          </span>
          <div>
            {user.name}
            <small>{project ? label(project.role) : user.email}</small>
          </div>
          <button
            type="button"
            className="sign-out"
            title="Sign out"
            onClick={async () => {
              await call("/auth/logout", {});
              local.clear();
              navigate("/");
            }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="surface">
        <div className="topbar">
          <Link to="/">Projects</Link>
          <ChevronRight size={13} />
          <span>{project?.name ?? "Directory"}</span>
          {project?.lab && (
            <span className="environment">
              <span /> Synthetic workspace
            </span>
          )}
        </div>
        <main>
          <ErrorMessage error={projects.error} />
          {projects.isPending ? (
            <p>Loading projects…</p>
          ) : (
            <Routes>
              <Route
                path="/"
                element={<Projects projects={projects.data ?? []} />}
              />
              {project && (
                <>
                  <Route path={base} element={<Overview project={project} />} />
                  <Route
                    path={base + "/research"}
                    element={<Research key={project.id} project={project} />}
                  />
                  <Route
                    path={base + "/answers/:answerId"}
                    element={<AnswerRoute project={project} />}
                  />
                  <Route
                    path={base + "/sources"}
                    element={<Sources key={project.id} project={project} />}
                  />
                  <Route
                    path={base + "/sources/:sourceId"}
                    element={<Document project={project} />}
                  />
                  <Route
                    path={base + "/ingestion"}
                    element={<Ingestion project={project} />}
                  />
                  <Route
                    path={base + "/claims"}
                    element={<Registry project={project} />}
                  />
                  <Route
                    path={base + "/contradictions"}
                    element={<Registry project={project} contradictions />}
                  />
                  <Route
                    path={base + "/reports"}
                    element={<Reports project={project} />}
                  />
                  <Route
                    path={base + "/reports/:reportId"}
                    element={<ReportDetail project={project} />}
                  />
                  <Route
                    path={base + "/lab"}
                    element={<Lab project={project} />}
                  />
                  <Route
                    path={base + "/evaluation"}
                    element={<Evaluation project={project} />}
                  />
                  <Route
                    path={base + "/admin"}
                    element={<Administration project={project} user={user} />}
                  />
                </>
              )}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
        </main>
      </div>
    </div>
  );
}

function Projects({ projects }: { projects: Project[] }) {
  const local = useQueryClient();
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>();
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    try {
      const result = await call<{ id: string }>("/projects", {
        name: fd.get("name"),
        description: fd.get("description"),
      });
      await local.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects/" + result.id);
    } catch (err) {
      setError(err);
    }
  }
  return (
    <>
      <Header
        eyebrow="Research portfolio"
        title="Projects"
        text="Open a workspace to inspect research, sources and decisions."
      />
      <div className="project-grid">
        {projects.map((project) => (
          <Link
            key={project.id}
            className="panel project-card"
            to={"/projects/" + project.id}
          >
            <span className="category">
              <FolderOpen size={15} /> {label(project.role)}
            </span>
            <h2>{project.name}</h2>
            <p>{project.description}</p>
            <span className="go">
              Open workspace <ArrowRight size={16} />
            </span>
          </Link>
        ))}
      </div>
      <details className="panel disclosure">
        <summary>Create project</summary>
        <form className="stack" onSubmit={add}>
          <label>
            Project name
            <input name="name" required />
          </label>
          <label>
            Description
            <textarea name="description" />
          </label>
          <button className="primary">Create project</button>
          <ErrorMessage error={error} />
        </form>
      </details>
    </>
  );
}

function Overview({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const records = useQuery({
    queryKey: [project.id, "answers"],
    queryFn: () => call<AnswerItem[]>(base + "/answers"),
  });
  const sources = useQuery({
    queryKey: [project.id, "sources"],
    queryFn: () => call<Source[]>(base + "/sources"),
  });
  return (
    <>
      <Header
        eyebrow="Research overview"
        title={project.name}
        text={project.description}
        action={
          <Link className="primary" to={base + "/research"}>
            Open research desk <ArrowRight size={17} />
          </Link>
        }
      />
      <div className="overview-grid">
        <Link className="panel overview-card" to={base + "/sources"}>
          <BookOpen />
          <h2>Source library</h2>
          <p>{sources.data?.length ?? "…"} sources in the current view</p>
          <span className="go">
            Review documents <ArrowRight size={15} />
          </span>
        </Link>
        <Link className="panel overview-card" to={base + "/claims"}>
          <ClipboardCheck />
          <h2>Claims & review</h2>
          <p>{records.data?.length ?? "…"} saved answers in the current view</p>
          <span className="go">
            Open review queue <ArrowRight size={15} />
          </span>
        </Link>
      </div>
      <Registry project={project} compact />
    </>
  );
}

function Research({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const cache = useQueryClient();
  const [question, setQuestion] = useState(project.lab ? EXAMPLE : "");
  const [mode, setMode] = useState("hybrid");
  const [provider, setProvider] = useState("extractive");
  const [category, setCategory] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [answer, setAnswer] = useState<Answer>();
  const [hits, setHits] = useState<Hit[]>();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<unknown>();
  const models = useQuery({
    queryKey: ["models"],
    queryFn: () =>
      call<{ ollama_enabled: boolean; ollama_model: string }>("/models"),
  });
  async function run(kind: "answers" | "search") {
    if (question.trim().length < 2) return;
    setBusy(kind);
    setError(undefined);
    const payload = {
      query: question,
      mode,
      ...(category ? { category } : {}),
      ...(cutoff ? { as_of: new Date(cutoff).toISOString() } : {}),
    };
    try {
      if (kind === "answers") {
        setAnswer(
          await call<Answer>(base + "/answers", { ...payload, provider }),
        );
        setHits(undefined);
        await cache.invalidateQueries({ queryKey: [project.id, "answers"] });
      } else {
        setHits((await call<{ hits: Hit[] }>(base + "/search", payload)).hits);
        setAnswer(undefined);
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <Header
        eyebrow="Evidence workspace"
        title="Research desk"
        text="Ask a research question and trace the result to the exact text in versioned sources."
      />
      <form
        className="panel ask"
        onSubmit={(e) => {
          e.preventDefault();
          void run("answers");
        }}
      >
        <label htmlFor="question">Research question</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          required
          maxLength={500}
        />
        <div className="ask-toolbar">
          <label>
            Retrieval
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="hybrid">Hybrid</option>
              <option value="keyword">Keyword</option>
              <option value="semantic">Semantic</option>
            </select>
          </label>
          <label>
            Answer mode
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="extractive">Extractive</option>
              {models.data?.ollama_enabled && (
                <option value="ollama">
                  {models.data.ollama_model} · Ollama
                </option>
              )}
            </select>
          </label>
          <div className="actions">
            <button
              type="button"
              onClick={() => void run("search")}
              disabled={!!busy || question.trim().length < 2}
            >
              <Search size={16} /> Search sources
            </button>
            <button
              className="primary"
              disabled={!!busy || question.trim().length < 2}
            >
              {busy ? "Working…" : "Run analysis"} <ArrowRight size={16} />
            </button>
          </div>
        </div>
        <details className="filters">
          <summary>Filters and historical search</summary>
          <div className="filters-grid">
            <label>
              Category
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All sources</option>
                {[
                  "specification",
                  "test",
                  "architecture",
                  "meeting",
                  "advisory",
                  "other",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              As of
              <input
                type="datetime-local"
                value={cutoff}
                onChange={(e) => setCutoff(e.target.value)}
              />
            </label>
          </div>
        </details>
        <ErrorMessage error={error} />
      </form>
      {answer && (
        <AnswerView
          key={answer.id}
          project={project}
          answer={answer}
          summaryOnly
        />
      )}
      {hits && (
        <div className="panel results">
          <h2>
            Retrieved passages <span>{hits.length}</span>
          </h2>
          {hits.length === 0 && <p>No passages matched these filters.</p>}
          {hits.map((hit) => (
            <div className="result" key={hit.chunk_id}>
              <Link
                to={
                  base + "/sources/" + hit.source_id + "?version=" + hit.version
                }
              >
                {hit.title}
              </Link>
              <span className="meta">
                Version {hit.version} · {hit.heading} · score{" "}
                {hit.score.toFixed(3)}
              </span>
              <p>{hit.content}</p>
            </div>
          ))}
        </div>
      )}
      {!answer && !hits && (
        <section className="panel starter">
          <div className="project-icon">
            <Search size={20} />
          </div>
          <div>
            <h2>Start with a verifiable question</h2>
            <p>
              {project.lab
                ? "Northstar includes a target of 10 000 users and a load test at 2 000. Ask about the target to see how the evidence differs."
                : "Import text sources, then run a question or inspect search results."}
            </p>
          </div>
        </section>
      )}
    </>
  );
}

function AnswerRoute({ project }: { project: Project }) {
  const { answerId } = useParams();
  const { data, error, isPending } = useQuery({
    queryKey: [project.id, "answer", answerId],
    queryFn: () =>
      call<Answer>("/projects/" + project.id + "/answers/" + answerId),
  });
  return (
    <>
      <Header
        eyebrow="Research record"
        title="Answer details"
        text={data?.query}
      />
      <ErrorMessage error={error} />
      {isPending && <p>Loading answer…</p>}
      {data && <AnswerView project={project} answer={data} />}
    </>
  );
}

function CitationInspector({
  project,
  citation,
  answerId,
}: {
  project: Project;
  citation: Citation;
  answerId: string;
}) {
  const [message, setMessage] = useState("");
  const base = "/projects/" + project.id;
  async function verify() {
    try {
      const checked = await call<Citation>(base + "/citations/verify", {
        answer_id: answerId,
        chunk_id: citation.chunk_id,
        quote: citation.quote,
        version_id: citation.version_id,
        content_hash: citation.content_hash,
      });
      setMessage(
        checked.integrity === "VALID"
          ? "Exact text, range and run context verified."
          : "Citation integrity check failed.",
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Verification failed");
    }
  }
  return (
    <div className="citation-detail">
      <div className="citation-state">
        <Badge value={citation.integrity} />
        <Badge value={citation.freshness} />
      </div>
      <blockquote>{citation.quote}</blockquote>
      <dl>
        <dt>Version</dt>
        <dd>{citation.version}</dd>
        <dt>Section</dt>
        <dd>
          {citation.heading}
          {citation.page && " · Page " + citation.page}
        </dd>
        <dt>Character range</dt>
        <dd>
          {citation.start_at}–{citation.end_at}
        </dd>
        <dt>SHA-256</dt>
        <dd className="hash">{citation.content_hash}</dd>
      </dl>
      <div className="citation-actions">
        <Link
          to={
            base +
            "/sources/" +
            citation.source_id +
            "?version=" +
            citation.version +
            "&start=" +
            citation.start_at +
            "&end=" +
            citation.end_at
          }
        >
          Open source <ArrowRight size={15} />
        </Link>
        <button type="button" onClick={() => void verify()}>
          <ShieldCheck size={15} /> Verify
        </button>
      </div>
      {message && <p role="status">{message}</p>}
    </div>
  );
}

function AnswerView({
  project,
  answer,
  summaryOnly = false,
}: {
  project: Project;
  answer: Answer;
  summaryOnly?: boolean;
}) {
  const base = "/projects/" + project.id;
  const sortedCites = [...answer.citations].sort(
    (a, b) =>
      Number(b.title.startsWith("Load test")) -
      Number(a.title.startsWith("Load test")),
  );
  const positive = answer.output.claims.flatMap((claim) => claim.evidence);
  const findings = positive.filter(
    (fact, index) =>
      positive.findIndex(
        (f) => f.value === fact.value && f.modality === fact.modality,
      ) === index,
  );
  const [selected, select] = useState<string | undefined>(sortedCites[0]?.id);
  const cite =
    sortedCites.find((entry) => entry.id === selected) ?? sortedCites[0];
  return (
    <>
      <div className="answer-grid">
        <section className="panel assessment">
          <div className="section-line">
            <div className="eyebrow">
              <ClipboardCheck size={15} /> Evidence assessment
            </div>
            <Badge value={answer.output.assessment} />
          </div>
          <h2>{answer.output.summary}</h2>
          <p className="meta">
            {answer.provider === "extractive"
              ? "Deterministic evidence rules"
              : answer.model + " · local generation"}{" "}
            · {answer.context.length} retrieved passages
          </p>
          {answer.output.generation && (
            <div className="generation">
              <Badge value={answer.output.generation.status} />
              {answer.output.generation.candidate && (
                <p>{answer.output.generation.candidate}</p>
              )}
            </div>
          )}
          <div className="findings">
            {findings.map((fact) => (
              <div className="finding" key={fact.value + fact.modality}>
                <span className="finding-icon">
                  {fact.modality === "observation" ? (
                    <Check size={17} />
                  ) : (
                    <FileText size={17} />
                  )}
                </span>
                <div>
                  <strong>
                    {Number.isNaN(Number(fact.value))
                      ? fact.value
                      : Number(fact.value).toLocaleString("en-GB")}{" "}
                    {fact.unit === "users"
                      ? "concurrent users"
                      : fact.unit === "percent"
                        ? "%"
                        : ""}
                  </strong>
                  <small>
                    {label(fact.modality)} · {fact.context}
                  </small>
                </div>
                {sortedCites.find((c) => c.chunk_id === fact.chunk_id) && (
                  <button
                    type="button"
                    title="Inspect evidence"
                    onClick={() =>
                      select(
                        sortedCites.find((c) => c.chunk_id === fact.chunk_id)
                          ?.id,
                      )
                    }
                  >
                    <ChevronRight size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
          {summaryOnly && (
            <Link className="go" to={base + "/answers/" + answer.id}>
              Open full research record <ArrowRight size={16} />
            </Link>
          )}
        </section>
        <section className="panel inspector">
          <div className="section-line">
            <h2>Citation inspector</h2>
            <span className="counter">{sortedCites.length}</span>
          </div>
          {cite ? (
            <>
              <label className="sr-only" htmlFor="citation">
                Citation source
              </label>
              <select
                id="citation"
                value={cite.id}
                onChange={(e) => select(e.target.value)}
              >
                {sortedCites.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
              <CitationInspector
                key={cite.id}
                project={project}
                citation={cite}
                answerId={answer.id}
              />
            </>
          ) : (
            <p className="empty">
              No passages qualified as evidence for the requested claim.
            </p>
          )}
        </section>
      </div>
      {!summaryOnly && (
        <>
          <Comparisons answer={answer} />
          <ReviewPanel project={project} answer={answer} />
        </>
      )}
    </>
  );
}

function Comparisons({ answer }: { answer: Answer }) {
  return (
    <section className="panel results">
      <h2>Evidence comparisons</h2>
      {answer.output.contradictions.length === 0 && (
        <p className="empty">
          No comparable disagreements were found in this run.
        </p>
      )}
      {answer.output.contradictions.map((item, i) => (
        <article className="result" key={i}>
          <Badge value={item.type} />
          <p>{item.reason}</p>
          <div className="compare-grid">
            {[item.left, item.right].map((fact, side) => {
              const cite = answer.citations.find(
                (c) => c.chunk_id === fact.chunk_id,
              );
              return (
                <blockquote key={side}>
                  {fact.text}
                  <small>
                    {cite?.title} · {fact.context}
                  </small>
                </blockquote>
              );
            })}
          </div>
        </article>
      ))}
    </section>
  );
}

function ReviewPanel({
  project,
  answer,
}: {
  project: Project;
  answer: Answer;
}) {
  const cache = useQueryClient();
  const base = "/projects/" + project.id;
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const state = answer.reviews.at(-1)?.decision ?? "AUTO_ASSESSED";
  const dispatch = state === "AUTO_ASSESSED" || state === "NEEDS_MORE_EVIDENCE";
  const canDecide =
    state === "IN_REVIEW" && ["ADMIN", "REVIEWER"].includes(project.role);
  async function review(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const form = e.currentTarget;
    const data = new FormData(form);
    try {
      await call(base + "/answers/" + answer.id + "/reviews", {
        decision: dispatch ? "IN_REVIEW" : data.get("decision"),
        rationale: data.get("rationale"),
        revision: answer.reviews.length,
      });
      form.reset();
      await cache.invalidateQueries({ queryKey: [project.id] });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  async function report(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const data = new FormData(e.currentTarget);
    try {
      const result = await call<{ id: string }>(base + "/reports", {
        answer_id: answer.id,
        title: data.get("title"),
        notes: data.get("notes"),
      });
      await cache.invalidateQueries({ queryKey: [project.id, "reports"] });
      navigate(base + "/reports/" + result.id);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="compare-grid">
      <section className="panel results">
        <div className="section-line">
          <h2>Human review</h2>
          <Badge value={state} />
        </div>
        {answer.reviews.map((entry) => (
          <div className="result" key={entry.id}>
            <strong>{label(entry.decision)}</strong>
            <p>{entry.rationale}</p>
            <small>{entry.author}</small>
          </div>
        ))}
        {answer.reviews.length === 0 && (
          <p className="empty">Review history is empty.</p>
        )}
        {(dispatch || canDecide) && (
          <form className="stack" onSubmit={review}>
            {canDecide && (
              <label>
                Decision
                <select name="decision">
                  <option value="VERIFIED">Verified</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="NEEDS_MORE_EVIDENCE">
                    Needs more evidence
                  </option>
                </select>
              </label>
            )}
            <label>
              Rationale
              <textarea name="rationale" minLength={5} required />
            </label>
            <button className="primary" disabled={busy}>
              {dispatch ? "Submit for review" : "Record decision"}
            </button>
          </form>
        )}
        <ErrorMessage error={error} />
      </section>
      {["ADMIN", "RESEARCHER"].includes(project.role) && (
        <section className="panel results">
          <h2>Research report</h2>
          <form className="stack" onSubmit={report}>
            <label>
              Report title
              <input name="title" required />
            </label>
            <label>
              Research notes
              <textarea name="notes" />
            </label>
            <button disabled={busy} className="primary">
              Save report snapshot
            </button>
          </form>
        </section>
      )}
    </div>
  );
}

function Registry({
  project,
  compact = false,
  contradictions = false,
}: {
  project: Project;
  compact?: boolean;
  contradictions?: boolean;
}) {
  const base = "/projects/" + project.id;
  const [selected, select] = useState("");
  const { data, error, isPending } = useQuery({
    queryKey: [project.id, "answers"],
    queryFn: () => call<AnswerItem[]>(base + "/answers"),
  });
  const detail = useQuery({
    queryKey: [project.id, "answer", selected],
    enabled: !!selected && contradictions,
    queryFn: () => call<Answer>(base + "/answers/" + selected),
  });
  return (
    <>
      {!compact && (
        <Header
          eyebrow="Evidence records"
          title={contradictions ? "Contradiction explorer" : "Claims & review"}
          text={
            contradictions
              ? "Compare passages under the conditions recorded in each source."
              : "Open an answer to inspect claims and record a review decision."
          }
        />
      )}
      <section className="panel results">
        {compact && <h2>Recent research</h2>}
        <ErrorMessage error={error} />
        {isPending && <p>Loading records…</p>}
        {data?.length === 0 && <p className="empty">No research runs yet.</p>}
        {data?.slice(0, compact ? 5 : undefined).map((entry) => (
          <div className="result record" key={entry.id}>
            <div>
              {contradictions ? (
                <button type="button" onClick={() => select(entry.id)}>
                  {entry.query}
                </button>
              ) : (
                <Link to={base + "/answers/" + entry.id}>{entry.query}</Link>
              )}
              <span className="meta">
                {date(entry.created_at)} · {label(entry.decision)}
              </span>
            </div>
            <Badge value={entry.assessment} />
          </div>
        ))}
      </section>
      {contradictions && (
        <>
          <ErrorMessage error={detail.error} />
          {detail.data && <Comparisons answer={detail.data} />}
        </>
      )}
    </>
  );
}

function Sources({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const cache = useQueryClient();
  const [error, setError] = useState<unknown>();
  const [uploaded, setUploaded] = useState(false);
  const [archived, setArchived] = useState(false);
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const {
    data,
    error: loadError,
    isPending,
  } = useQuery({
    queryKey: [project.id, "sources", offset, archived],
    queryFn: () =>
      call<Source[]>(
        base + "/sources?offset=" + offset + "&archived=" + archived,
      ),
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.version === null) ? 2500 : false,
  });
  async function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(undefined);
    setUploaded(false);
    setBusy(true);
    const form = e.currentTarget;
    try {
      await call(base + "/documents", new FormData(form));
      form.reset();
      setUploaded(true);
      await cache.invalidateQueries({ queryKey: [project.id] });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header
        eyebrow="Document corpus"
        title="Source library"
        text="Versioned originals and their searchable text."
      />
      {["ADMIN", "RESEARCHER"].includes(project.role) && (
        <details className="panel disclosure">
          <summary>Upload source or add a version</summary>
          <form className="stack" onSubmit={send}>
            <label>
              Source title
              <input name="title" required />
            </label>
            <label>
              Category
              <select name="category">
                {[
                  "specification",
                  "test",
                  "architecture",
                  "meeting",
                  "advisory",
                  "other",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Original file
              <input
                name="file"
                type="file"
                accept=".txt,.md,.html,.pdf,.docx"
                required
              />
            </label>
            <button className="primary" disabled={busy}>
              Queue import
            </button>
            {uploaded && (
              <p role="status">
                Import queued.{" "}
                <Link to={base + "/ingestion"}>Monitor processing</Link>
              </p>
            )}
            <ErrorMessage error={error} />
          </form>
        </details>
      )}
      <section className="panel results">
        <div className="section-line">
          <h2>Sources</h2>
          <label className="check">
            <input
              type="checkbox"
              checked={archived}
              onChange={(e) => {
                setArchived(e.target.checked);
                setOffset(0);
              }}
            />{" "}
            Include archived
          </label>
        </div>
        <ErrorMessage error={loadError} />
        {isPending && <p>Loading source library…</p>}
        {data?.length === 0 && <p>No sources on this page.</p>}
        {data?.map((row) => (
          <div className="result record" key={row.id}>
            <div>
              <Link to={base + "/sources/" + row.id}>{row.title}</Link>
              <span className="meta">{row.category}</span>
            </div>
            <span>
              {row.archived_at
                ? "Archived"
                : row.version
                  ? "Version " + row.version
                  : "Awaiting import"}
            </span>
          </div>
        ))}
        <div className="actions pagination">
          <button
            type="button"
            disabled={!offset}
            onClick={() => setOffset(offset - 50)}
          >
            Previous
          </button>
          <button
            type="button"
            disabled={data?.length !== 50}
            onClick={() => setOffset(offset + 50)}
          >
            Next
          </button>
        </div>
      </section>
    </>
  );
}

function Document({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const { sourceId } = useParams();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const location = useLocation();
  const [compare, setCompare] = useState(0);
  const [actionError, setActionError] = useState<unknown>();
  const search = new URLSearchParams(location.search);
  const entry = useQuery({
    queryKey: [project.id, "source", sourceId],
    queryFn: () =>
      call<{ source: Source; versions: Version[] }>(
        base + "/sources/" + sourceId + "/versions",
      ),
  });
  const version =
    Number(search.get("version")) || entry.data?.versions[0]?.version || 0;
  const root = base + "/sources/" + sourceId + "/versions/";
  const content = useQuery({
    queryKey: [project.id, "version", sourceId, version],
    enabled: version > 0,
    queryFn: () => call<Version>(root + version),
  });
  const old = useQuery({
    queryKey: [project.id, "version", sourceId, compare],
    enabled: compare > 0,
    queryFn: () => call<Version>(root + compare),
  });
  const start = Number(search.get("start"));
  const end = Number(search.get("end"));
  const chars = Array.from(content.data?.normalized ?? "");
  async function archive() {
    if (
      !window.confirm("Archive this source and hide it from current searches?")
    )
      return;
    try {
      await call(base + "/sources/" + sourceId, undefined, "DELETE");
      await cache.invalidateQueries({ queryKey: [project.id] });
    } catch (err) {
      setActionError(err);
    }
  }
  return (
    <>
      <Link className="back" to={base + "/sources"}>
        <ArrowLeft size={15} /> Source library
      </Link>
      <Header
        eyebrow="Document viewer"
        title={entry.data?.source.title ?? "Source document"}
        action={
          version > 0 && (
            <a
              className="button"
              href={"/api/v1" + root + version + "/original"}
            >
              <ArrowDownToLine size={17} /> Original file
            </a>
          )
        }
      />
      <ErrorMessage
        error={entry.error ?? content.error ?? old.error ?? actionError}
      />
      {entry.isPending && <p>Loading document…</p>}
      {entry.data && (
        <div className="panel results">
          <div className="filters-grid">
            <label>
              Version
              <select
                value={version}
                onChange={(e) => navigate("?version=" + e.target.value)}
              >
                {entry.data.versions.map((v) => (
                  <option value={v.version} key={v.version}>
                    Version {v.version} · {date(v.created_at)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Compare with
              <select
                value={compare}
                onChange={(e) => setCompare(Number(e.target.value))}
              >
                <option value="0">Single version</option>
                {entry.data.versions
                  .filter((v) => v.version !== version)
                  .map((v) => (
                    <option value={v.version} key={v.version}>
                      Version {v.version}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          <div className={old.data ? "compare-grid" : ""}>
            {content.data && (
              <article className="document">
                <span className="eyebrow">Version {version}</span>
                <pre>
                  {end > start ? (
                    <>
                      {chars.slice(0, start).join("")}
                      <mark>{chars.slice(start, end).join("")}</mark>
                      {chars.slice(end).join("")}
                    </>
                  ) : (
                    content.data.normalized
                  )}
                </pre>
              </article>
            )}
            {old.data && (
              <article className="document">
                <span className="eyebrow">Version {compare}</span>
                <pre>{old.data.normalized}</pre>
              </article>
            )}
          </div>
          {!entry.data.source.archived_at &&
            ["ADMIN", "RESEARCHER"].includes(project.role) && (
              <button type="button" onClick={() => void archive()}>
                Archive source
              </button>
            )}
        </div>
      )}
    </>
  );
}

function Ingestion({ project }: { project: Project }) {
  const data = useQuery({
    queryKey: [project.id, "jobs"],
    refetchInterval: 2500,
    queryFn: () =>
      call<
        {
          id: string;
          title: string;
          filename: string;
          state: string;
          error: string | null;
        }[]
      >("/projects/" + project.id + "/jobs"),
  });
  return (
    <>
      <Header
        eyebrow="Document corpus"
        title="Ingestion monitor"
        text="Track file parsing and indexing."
      />
      <section className="panel results">
        <ErrorMessage error={data.error} />
        {data.isPending && <p>Loading jobs…</p>}
        {data.data?.length === 0 && <p>No import jobs.</p>}
        {data.data?.map((job) => (
          <div className="result record" key={job.id}>
            <div>
              <strong>{job.title}</strong>
              <span className="meta">{job.error ?? job.filename}</span>
            </div>
            <Badge value={job.state} />
          </div>
        ))}
      </section>
    </>
  );
}

type ReportList = { id: string; title: string; created_at: string };
type Snapshot = {
  id: string;
  revision: number;
  body: Answer & { notes: string };
  created_at: string;
};
function Reports({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const data = useQuery({
    queryKey: [project.id, "reports"],
    queryFn: () => call<ReportList[]>(base + "/reports"),
  });
  return (
    <>
      <Header
        eyebrow="Research archive"
        title="Reports"
        text="Open an immutable snapshot of research and decisions."
      />
      <section className="panel results">
        <ErrorMessage error={data.error} />
        {data.isPending && <p>Loading reports…</p>}
        {data.data?.length === 0 && (
          <p>No reports yet. Create a snapshot from an answer.</p>
        )}
        {data.data?.map((item) => (
          <div className="result record" key={item.id}>
            <Link to={base + "/reports/" + item.id}>{item.title}</Link>
            <span>{date(item.created_at)}</span>
          </div>
        ))}
      </section>
    </>
  );
}
function ReportDetail({ project }: { project: Project }) {
  const { reportId } = useParams();
  const base = "/projects/" + project.id + "/reports/" + reportId;
  const [revision, setRevision] = useState(0);
  const [compare, setCompare] = useState(0);
  const [error, setError] = useState<unknown>();
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: [project.id, "report", reportId],
    queryFn: () => call<ReportList & { snapshots: Snapshot[] }>(base),
  });
  const answers = useQuery({
    queryKey: [project.id, "answers"],
    queryFn: () => call<AnswerItem[]>("/projects/" + project.id + "/answers"),
  });
  const snapshots = result.data?.snapshots ?? [];
  const visible =
    snapshots.find((item) => item.revision === revision) ?? snapshots[0];
  const old = snapshots.find((item) => item.revision === compare);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    try {
      const data = new FormData(form);
      if (!data.get("answer_id")) data.delete("answer_id");
      await call(base + "/snapshots", data);
      form.reset();
      setRevision(0);
      setCompare(0);
      await cache.invalidateQueries({
        queryKey: [project.id, "report", reportId],
      });
    } catch (err) {
      setError(err);
    }
  }
  return (
    <>
      <Header
        eyebrow="Research archive"
        title={result.data?.title ?? "Report"}
        text={visible?.body.query}
      />
      <ErrorMessage error={result.error ?? error} />
      {result.isPending && <p>Loading snapshots…</p>}
      <section className="panel results">
        <div className="filters-grid">
          <label>
            Snapshot
            <select
              value={visible?.revision ?? 0}
              onChange={(e) => setRevision(Number(e.target.value))}
            >
              {snapshots.map((item) => (
                <option key={item.id} value={item.revision}>
                  Snapshot {item.revision}
                </option>
              ))}
            </select>
          </label>
          <label>
            Compare with
            <select
              value={compare}
              onChange={(e) => setCompare(Number(e.target.value))}
            >
              <option value={0}>Single snapshot</option>
              {snapshots
                .filter((item) => item.revision !== visible?.revision)
                .map((item) => (
                  <option key={item.id} value={item.revision}>
                    Snapshot {item.revision}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="compare-grid">
          {[visible, old]
            .filter((item): item is Snapshot => !!item)
            .map((item) => (
              <article className="document" key={item.id}>
                <span className="eyebrow">
                  Snapshot {item.revision} · {date(item.created_at)}
                </span>
                <p>{item.body.output.summary}</p>
                <p>{item.body.notes}</p>
                <p>
                  {label(item.body.reviews.at(-1)?.decision ?? "AUTO_ASSESSED")}
                </p>
                {item.body.citations.map((c) => (
                  <p key={c.id}>
                    <a href={c.original_url}>
                      {c.title} · v{c.version}
                    </a>
                  </p>
                ))}
                <a
                  className="go"
                  href={
                    "/api/v1" + base + "/snapshots/" + item.revision + "/export"
                  }
                >
                  Download JSON <ArrowDownToLine size={16} />
                </a>
                <a
                  className="go"
                  href={
                    "/api/v1" +
                    base +
                    "/snapshots/" +
                    item.revision +
                    "/export?format=md"
                  }
                >
                  Download Markdown <ArrowDownToLine size={16} />
                </a>
              </article>
            ))}
        </div>
        {["ADMIN", "RESEARCHER"].includes(project.role) && (
          <form className="stack" onSubmit={save}>
            <label>
              Answer for next snapshot
              <select name="answer_id">
                <option value="">Original research answer</option>
                {answers.data?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.query} · {date(item.created_at)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Notes for next snapshot
              <textarea name="notes" />
            </label>
            <button className="primary">Save new snapshot</button>
          </form>
        )}
      </section>
    </>
  );
}

function Evaluation({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const cache = useQueryClient();
  const [mode, setMode] = useState("hybrid");
  const [provider, setProvider] = useState("extractive");
  const [selected, select] = useState<Eval>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const history = useQuery({
    queryKey: [project.id, "evaluations"],
    queryFn: () => call<Eval[]>(base + "/evaluations"),
  });
  const models = useQuery({
    queryKey: ["models"],
    queryFn: () => call<{ ollama_enabled: boolean }>("/models"),
  });
  const current = selected ?? history.data?.[0];
  async function run(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      select(await call<Eval>(base + "/evaluations", { mode, provider }));
      await cache.invalidateQueries({ queryKey: [project.id, "evaluations"] });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header
        eyebrow="Quality evaluation"
        title="Evaluation"
        text="Measure retrieval and citation integrity against a labelled dataset."
      />
      <form className="panel results ask-toolbar" onSubmit={run}>
        <label>
          Retrieval
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option>hybrid</option>
            <option>keyword</option>
            <option>semantic</option>
          </select>
        </label>
        <label>
          Answer mode
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            <option>extractive</option>
            {models.data?.ollama_enabled && <option>ollama</option>}
          </select>
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Running…" : "Run evaluation"} <ArrowRight size={15} />
        </button>
      </form>
      <ErrorMessage error={error ?? history.error} />
      {current && (
        <section className="panel results">
          <div className="section-line">
            <h2>Evaluation results</h2>
            <span className="meta">
              {current.configuration.dataset} · {current.configuration.mode}
            </span>
          </div>
          <div className="metric-grid">
            {Object.entries(current.results.metrics).map(([key, value]) => (
              <div key={key}>
                <strong>
                  {value === null ? "—" : Math.round(value * 100) + "%"}
                </strong>
                <span>{label(key)}</span>
              </div>
            ))}
          </div>
          {current.results.cases.map((item) => (
            <div key={item.case} className="result record">
              <div>
                <Link to={base + "/answers/" + item.answer_id}>
                  {item.question}
                </Link>
                <span className="meta">
                  Expected {label(item.expected)} · observed{" "}
                  {label(item.actual)} · {item.valid}/{item.citations} valid
                  citations
                </span>
                <span className="meta">{item.sources.join(" · ")}</span>
              </div>
              <Badge value={item.correct ? "VERIFIED" : "FAILED"} />
            </div>
          ))}
        </section>
      )}
      {history.data && history.data.length > 0 && (
        <section className="panel results">
          <h2>Run history</h2>
          {history.data.map((item, i) => (
            <div className="result" key={item.id}>
              <button onClick={() => select(item)}>
                {i + 1}. {item.configuration.mode} ·{" "}
                {item.configuration.provider} · {item.id.slice(0, 8)}
              </button>
            </div>
          ))}
        </section>
      )}
    </>
  );
}

function Lab({ project }: { project: Project }) {
  const base = "/projects/" + project.id;
  const cache = useQueryClient();
  const [active, setActive] = useState<LabRun>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const history = useQuery({
    queryKey: [project.id, "lab"],
    queryFn: () => call<LabRun[]>(base + "/lab"),
  });
  const current = active ?? history.data?.[0];
  async function run() {
    setBusy(true);
    setError(undefined);
    try {
      setActive(await call<LabRun>(base + "/lab", {}));
      await cache.invalidateQueries({ queryKey: [project.id, "lab"] });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header
        eyebrow="Synthetic workspace"
        title="Veridion Lab"
        text="Run checks against a fresh Northstar corpus in PostgreSQL. Scenario data is rolled back after each batch."
        action={
          <button
            className="primary"
            type="button"
            disabled={busy}
            onClick={() => void run()}
          >
            <FlaskConical size={16} />
            {busy ? "Running scenarios…" : "Run scenarios"}
          </button>
        }
      />
      <ErrorMessage error={history.error ?? error} />
      {history.isPending && <p>Loading scenario history…</p>}
      {current ? (
        <section className="panel results">
          <div className="section-line">
            <h2>Scenario results</h2>
            <span className="meta">
              {current.results.filter((item) => item.passed).length} of{" "}
              {current.results.length} passed
            </span>
          </div>
          {current.results.map((item) => (
            <details className="result" key={item.scenario}>
              <summary>
                {item.scenario}{" "}
                <Badge value={item.passed ? "VERIFIED" : "FAILED"} />
              </summary>
              <p>{item.expectation}</p>
              {item.sources.length > 0 && (
                <p>Sources · {item.sources.join(" · ")}</p>
              )}
              <pre className="observed">
                {JSON.stringify(item.observed, null, 2)}
              </pre>
            </details>
          ))}
        </section>
      ) : (
        <section className="panel results">
          <h2>Scenario history</h2>
          <p>No run has been recorded.</p>
        </section>
      )}
      {!!history.data?.length && (
        <section className="panel results">
          <h2>Run history</h2>
          {history.data.map((item) => (
            <div className="result" key={item.id}>
              <button type="button" onClick={() => setActive(item)}>
                {item.id.slice(0, 8)} ·{" "}
                {item.results.filter((check) => check.passed).length} passed
              </button>
            </div>
          ))}
        </section>
      )}
    </>
  );
}

function Administration({ project, user }: { project: Project; user: User }) {
  const base = "/projects/" + project.id;
  const cache = useQueryClient();
  const [error, setError] = useState<unknown>();
  const [message, setMessage] = useState("");
  const audit = useQuery({
    queryKey: [project.id, "audit"],
    queryFn: () =>
      call<
        {
          id: number;
          actor: string;
          action: string;
          request_id: string;
          created_at: string;
        }[]
      >(base + "/audit"),
  });
  const members = useQuery({
    queryKey: [project.id, "members"],
    queryFn: () =>
      call<{ id: string; name: string; role: string; email: string }[]>(
        base + "/members",
      ),
  });
  async function submit(
    e: FormEvent<HTMLFormElement>,
    kind: "member" | "user",
  ) {
    e.preventDefault();
    setMessage("");
    setError(undefined);
    const form = e.currentTarget;
    try {
      await call(
        kind === "member" ? base + "/members" : "/users",
        Object.fromEntries(new FormData(form)),
        kind === "member" ? "PUT" : "POST",
      );
      form.reset();
      setMessage(kind === "member" ? "Role assigned." : "User created.");
      await cache.invalidateQueries({ queryKey: [project.id] });
    } catch (err) {
      setError(err);
    }
  }
  return (
    <>
      <Header
        eyebrow="Project governance"
        title="Administration"
        text="Manage membership and inspect the project audit trail."
      />
      <ErrorMessage error={error ?? audit.error ?? members.error} />
      {message && <p role="status">{message}</p>}
      <div className="compare-grid">
        <section className="panel results">
          <h2>Members</h2>
          {members.data?.map((member) => (
            <div className="result record" key={member.id}>
              <div>
                {member.name}
                <span className="meta">{member.email}</span>
              </div>
              <span>{label(member.role)}</span>
            </div>
          ))}
          <form className="stack" onSubmit={(e) => void submit(e, "member")}>
            <label>
              Email
              <input type="email" name="email" required />
            </label>
            <label>
              Role
              <select name="role">
                {["RESEARCHER", "ANALYST", "REVIEWER", "ADMIN"].map((role) => (
                  <option key={role}>{role}</option>
                ))}
              </select>
            </label>
            <button className="primary">Assign role</button>
          </form>
        </section>
        {user.is_admin && (
          <section className="panel results">
            <h2>New user</h2>
            <form className="stack" onSubmit={(e) => void submit(e, "user")}>
              <label>
                Name
                <input name="name" required />
              </label>
              <label>
                Email
                <input type="email" name="email" required />
              </label>
              <label>
                Password
                <input
                  type="password"
                  name="password"
                  required
                  minLength={12}
                />
              </label>
              <button className="primary">Create user</button>
            </form>
          </section>
        )}
      </div>
      <section className="panel results">
        <h2>Audit history</h2>
        {audit.data?.map((event) => (
          <div className="result record" key={event.id}>
            <div>
              <strong>{event.action}</strong>
              <span className="meta">
                {event.actor} · {event.request_id}
              </span>
            </div>
            <span>{date(event.created_at)}</span>
          </div>
        ))}
        {audit.data?.length === 0 && <p>No audit entries.</p>}
      </section>
    </>
  );
}
function App() {
  const user = useQuery({
    queryKey: ["user"],
    queryFn: () => call<User>("/auth/me"),
  });
  if (user.isPending) return <div className="loading">Loading Veridion…</div>;
  if (
    !user.data &&
    user.error &&
    !(user.error instanceof ApiError && user.error.status === 401)
  ) {
    return (
      <div className="loading">
        <ErrorMessage error={user.error} />
        <button onClick={() => void user.refetch()}>Retry</button>
      </div>
    );
  }
  return user.data ? <Shell user={user.data} /> : <Login />;
}
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>,
);
