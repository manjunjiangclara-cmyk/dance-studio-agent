import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type DependencyList,
  type ReactNode,
} from "react";
import {
  Link,
  NavLink,
  Navigate,
  useBlocker,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  Database,
  FileText,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Mail,
  MailSearch,
  Menu,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { all, ApiError, examples, get, post, request } from "./data";
import { confirmedSessions } from "./attendance";
import { CustomEmail } from "./CustomEmail";
import { BookingProposal } from "./BookingProposal";
import { GuidedTour } from "./GuidedTour";
import {
  LiveReviewQueue,
  LiveReviewDetail,
  LiveReviewCases,
} from "./LiveReviewQueue";
import { PolicyPage } from "./PolicyPage";
import { DocumentsPage } from "./DocumentsPage";
import {
  DocumentAnswerEvidence,
  documentCitations,
  documentCitationUrl,
} from "./DocumentAnswerEvidence";
import { ClassificationPanel, IntentBadges } from "./Classification";
import { EnquiryPanel, missingTeacherDecisions } from "./EnquiryPanel";
import type { QuestionResolution } from "./types";
import type {
  Conversation,
  DatabaseRecord,
  DatabaseTable,
  Enrolment,
  Identity,
  Location,
  Message,
  Page,
  Run,
  RunStatus,
  RunSummary,
  Session,
  Student,
  StudentDetail,
  StudioClass,
  Term,
} from "./types";

const Context = createContext({
  workspace: false,
  base: "/demo",
  identity: { authenticated: false } as Identity,
});
const useSite = () => useContext(Context);
const statusLabel: Record<RunStatus, string> = {
  running: "Processing",
  awaiting_review: "Awaiting review",
  finalizing: "Saving memory",
  approved: "Approved",
  closed: "Closed",
  superseded: "Superseded",
  failed: "Needs attention",
};
const statuses = Object.keys(statusLabel) as RunStatus[];
const dateLabel = (date: string) =>
  new Intl.DateTimeFormat("en-AU", {
    dateStyle: "medium",
    timeZone: "Australia/Melbourne",
  }).format(new Date(date.length === 10 ? date + "T12:00:00+11:00" : date));
const timeLabel = (date: string, zone = "Australia/Melbourne") =>
  new Intl.DateTimeFormat("en-AU", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: zone,
  }).format(new Date(date));
const summary = (run: Run) =>
  typeof run.interpretation.request_summary === "string"
    ? run.interpretation.request_summary
    : "Review this enquiry.";

function useLoad<T>(
  loader: () => Promise<T>,
  dependencies: DependencyList,
  interval?: number,
) {
  const [value, setValue] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(undefined);
    loader()
      .then((next) => {
        if (active) setValue(next);
      })
      .catch((err) => {
        if (active) setError(err);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [...dependencies, tick]);
  useEffect(() => {
    if (!interval) return;
    const timer = window.setInterval(refresh, interval);
    return () => clearInterval(timer);
  }, [interval, refresh]);
  return { value, error, loading, refresh };
}

function Status({ status }: { status: RunStatus }) {
  return (
    <span className={`status status-${status}`}>
      <span />
      {statusLabel[status]}
    </span>
  );
}
function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <CircleHelp size={25} />
      <p>{children}</p>
    </div>
  );
}
function ErrorBox({ error, retry }: { error?: Error; retry?: () => void }) {
  if (!error) return null;
  return (
    <div className="notice error" role="alert">
      <strong>Something needs attention</strong>
      <p>{error.message}</p>
      {error instanceof ApiError && error.status === 401 && (
        <a className="button small secondary" href="/auth/login">
          Sign in again
        </a>
      )}
      {retry && (
        <button className="button small secondary" onClick={retry}>
          <RefreshCw size={14} />
          Try loading again
        </button>
      )}
    </div>
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      Loading records…
    </div>
  );
}
function PageHeader({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {action}
    </div>
  );
}
function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
function Pager({
  page,
  onChange,
}: {
  page: Page<unknown>;
  onChange: (offset: number) => void;
}) {
  if (!page.total) return null;
  return (
    <div className="pagination">
      <span>
        {page.offset + 1}–{Math.min(page.offset + page.limit, page.total)} of{" "}
        {page.total}
      </span>
      <div>
        <button
          aria-label="Previous page"
          disabled={!page.offset}
          onClick={() => onChange(Math.max(0, page.offset - page.limit))}
        >
          <ChevronLeft size={18} />
        </button>
        <button
          aria-label="Next page"
          disabled={page.offset + page.limit >= page.total}
          onClick={() => onChange(page.offset + page.limit)}
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const workspace =
    location.pathname === "/workspace" ||
    location.pathname.startsWith("/workspace/");
  const base = workspace ? "/workspace" : "/demo";
  const [identity, setIdentity] = useState<Identity>({ authenticated: false });
  const [authLoading, setAuthLoading] = useState(workspace);
  const [authError, setAuthError] = useState<Error>();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState<number>();
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const closeMenu = useCallback(() => {
    setMobileOpen(false);
    menuButton.current?.focus();
  }, []);
  useEffect(() => {
    const mobile = window.matchMedia("(max-width: 650px)");
    const onChange = () => {
      if (!mobile.matches) setMobileOpen(false);
    };
    mobile.addEventListener("change", onChange);
    return () => mobile.removeEventListener("change", onChange);
  }, []);
  useEffect(() => {
    if (!mobileOpen) return;
    closeButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (document.querySelector('[role="alertdialog"]')) return;
      if (event.key === "Escape") closeMenu();
      if (event.key === "Tab") {
        const focusable = sidebar.current?.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled])",
        );
        if (!focusable?.length) return;
        const first = focusable[0],
          last = focusable[focusable.length - 1];
        if (!sidebar.current?.contains(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen, closeMenu]);
  useEffect(() => {
    let active = true;
    setPendingCount(undefined);
    if (!workspace || !identity.authenticated) return;
    const load = () => {
      get<Page<RunSummary>>(workspace, "/agent-runs", {
        status: "awaiting_review",
        limit: 1,
      })
        .then((result) => {
          if (active) setPendingCount(result.total);
        })
        .catch(() => {
          if (active) setPendingCount(undefined);
        });
    };
    load();
    window.addEventListener("review-queue-changed", load);
    const timer = window.setInterval(load, 30_000);
    return () => {
      active = false;
      window.removeEventListener("review-queue-changed", load);
      window.clearInterval(timer);
    };
  }, [workspace, identity.authenticated, location.pathname]);
  useEffect(() => {
    let active = true;
    setMobileOpen(false);
    if (!workspace) {
      setAuthLoading(false);
      return;
    }
    setAuthLoading(true);
    setAuthError(undefined);
    request<Identity>("/auth/me")
      .then((user) => {
        if (active) setIdentity(user);
      })
      .catch((err) => {
        if (active) setAuthError(err);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    return () => {
      active = false;
    };
  }, [workspace]);
  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);
  const parts = location.pathname.split("/").filter(Boolean);
  const page = parts[1] || "overview",
    id = parts[2];
  const navigation = [
    ["overview", "Overview", LayoutDashboard],
    ["reviews", "Review queue", ClipboardCheck],
    ["students", "Students", Users],
    ["timetable", "Timetable", CalendarDays],
    ["database", "Database", Database],
    ["knowledge", "Studio knowledge", BookOpen],
    [
      "test-email",
      workspace ? "Test email" : "Email walkthrough",
      workspace ? FlaskConical : MailSearch,
    ],
  ] as const;
  const pageLabel =
    navigation.find(([path]) => path === page)?.[1] ||
    (page === "tour" ? "Guided demo" : "Overview");
  const detailLabel =
    id && page === "reviews"
      ? "Conversation review"
      : id && page === "students"
        ? "Student profile"
        : page === "knowledge" && id === "documents"
          ? "Documents"
          : page === "knowledge" && id === "rules"
            ? "Rules"
            : undefined;
  async function logout() {
    try {
      await post("/auth/logout", identity.csrf_token || "");
      setIdentity({ authenticated: false, login_available: true });
    } catch (err) {
      setAuthError(err as Error);
    }
  }
  return (
    <Context.Provider value={{ workspace, base, identity }}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app-shell">
        {mobileOpen && (
          <div
            className="sidebar-overlay"
            aria-hidden="true"
            onClick={closeMenu}
          />
        )}
        <aside
          ref={sidebar}
          id="main-sidebar"
          className={`sidebar ${mobileOpen ? "open" : ""}`}
        >
          <Link className="brand" to={base}>
            <span className="brand-mark" aria-hidden="true">
              S
            </span>
            <span>
              studio<span className="brand-light">copilot</span>
              <small>
                <Sparkles size={10} aria-hidden="true" /> AI FOR YOUR STUDIO
              </small>
            </span>
          </Link>
          <button
            ref={closeButton}
            className="mobile-close icon-button"
            aria-label="Close menu"
            onClick={closeMenu}
          >
            <X />
          </button>
          <nav aria-label="Main navigation">
            {[
              {
                label: workspace ? "WORKSPACE" : "EXPLORE",
                items: navigation.slice(0, 4),
              },
              { label: "STUDIO SETUP", items: [navigation[5], navigation[4]] },
              { label: "TOOLS", items: navigation.slice(6) },
            ].map((group) => (
              <div className="nav-group" key={group.label}>
                <div className="sidebar-label">{group.label}</div>
                {group.items.map(([path, label, Icon]) => (
                  <NavLink
                    key={path}
                    to={path === "overview" ? base : `${base}/${path}`}
                    end={path === "overview"}
                    className={({ isActive }) =>
                      isActive ? "nav-item active" : "nav-item"
                    }
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{label}</span>
                    {path === "reviews" &&
                      pendingCount !== undefined &&
                      pendingCount > 0 && (
                        <span
                          className="nav-count"
                          aria-label={`${pendingCount} awaiting review`}
                        >
                          {pendingCount}
                        </span>
                      )}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </aside>
        <div className="main-column">
          <header className="topbar">
            <button
              ref={menuButton}
              className="mobile-menu icon-button"
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              aria-controls="main-sidebar"
              onClick={() => setMobileOpen(true)}
            >
              <Menu />
            </button>
            <nav className="breadcrumb" aria-label="Breadcrumb">
              {detailLabel ? (
                <>
                  <Link to={`${base}/${page}`}>{pageLabel}</Link>
                  <span aria-hidden="true">/</span>
                  <span aria-current="page">{detailLabel}</span>
                </>
              ) : (
                <span aria-current="page">{pageLabel}</span>
              )}
            </nav>
            <div className="topbar-actions">
              <span className={`mode-badge ${workspace ? "owner-badge" : ""}`}>
                <span />
                {workspace ? "Owner workspace" : "Example data"}
              </span>
              {workspace && identity.authenticated ? (
                <button className="text-button" onClick={logout}>
                  <LogOut size={15} />
                  Sign out
                </button>
              ) : (
                <Link
                  className="owner-link"
                  to={workspace ? "/demo" : "/workspace"}
                >
                  {workspace ? "Public demo" : "Owner workspace"}
                  <ArrowUpRight size={14} />
                </Link>
              )}
            </div>
          </header>
          <main id="main" className="content" key={base}>
            {workspace && authLoading ? (
              <Loading />
            ) : workspace && !identity.authenticated ? (
              <div className="login-panel panel">
                <LockKeyhole size={32} />
                <div className="eyebrow">OWNER ACCESS</div>
                <h1>Your review workspace</h1>
                <p>
                  The public examples are open to everyone. Sign in as the
                  configured owner to inspect backend records and review live
                  drafts.
                </p>
                <ErrorBox error={authError} />
                {identity.login_available ? (
                  <a className="button primary" href="/auth/login">
                    Continue with Google <ArrowRight size={17} />
                  </a>
                ) : (
                  <div className="notice">
                    Owner sign-in is not configured on this instance. See the
                    website setup guide for Google credentials and the owner
                    email.
                  </div>
                )}
                <Link className="inline-link" to="/demo">
                  Explore the public examples <ArrowRight size={16} />
                </Link>
              </div>
            ) : (
              <>
                {workspace && (
                  <div className="workspace-note">
                    <ShieldCheck size={15} />
                    Signed in as {identity.user?.email}. Workspace records are
                    separate from published examples.
                  </div>
                )}
                <ErrorBox error={authError} />
                {page === "overview" ? (
                  <Overview />
                ) : page === "tour" && !workspace ? (
                  <GuidedTour />
                ) : page === "reviews" ? (
                  !workspace &&
                  (id === "live-booking" || id === "live-document") ? (
                    <LiveReviewDetail
                      key={id}
                      scenario={id === "live-booking" ? "booking" : "document"}
                    />
                  ) : id ? (
                    <ReviewDetail key={`${base}-${id}`} id={id} />
                  ) : workspace || location.search ? (
                    <ReviewQueue />
                  ) : (
                    <LiveReviewQueue />
                  )
                ) : page === "students" ? (
                  id ? (
                    <StudentPage key={`${base}-${id}`} id={id} />
                  ) : (
                    <Students />
                  )
                ) : page === "timetable" ? (
                  <Timetable />
                ) : page === "database" ? (
                  <DatabaseBrowser />
                ) : page === "policy" || page === "documents" ? (
                  <Navigate
                    to={`${base}/knowledge/${page === "policy" ? "rules" : "documents"}`}
                    replace
                  />
                ) : page === "knowledge" &&
                  (!id || id === "rules" || id === "documents") ? (
                  <>
                    <div className="page-heading">
                      <div>
                        <div className="eyebrow">YOUR STUDIO · AI CONTEXT</div>
                        <h1>Studio knowledge</h1>
                        <p>
                          Manage the rules and reference material for your
                          studio.
                        </p>
                      </div>
                    </div>
                    <nav
                      className="knowledge-nav"
                      aria-label="Studio knowledge"
                    >
                      <NavLink
                        to={`${base}/knowledge/rules`}
                        className={id !== "documents" ? "active" : ""}
                        aria-current={id !== "documents" ? "page" : undefined}
                      >
                        Rules
                      </NavLink>
                      <NavLink
                        to={`${base}/knowledge/documents`}
                        className={id === "documents" ? "active" : ""}
                      >
                        Documents
                      </NavLink>
                    </nav>
                    {id === "documents" ? (
                      <DocumentsPage
                        key={base}
                        workspace={workspace}
                        csrf={identity.csrf_token || ""}
                      />
                    ) : (
                      <PolicyPage
                        key={base}
                        workspace={workspace}
                        csrf={identity.csrf_token || ""}
                      />
                    )}
                  </>
                ) : page === "test-email" ? (
                  <TestEmail />
                ) : (
                  <Empty>
                    This page does not exist. Use the navigation to explore the
                    project.
                  </Empty>
                )}
              </>
            )}
          </main>
          <footer className="page-footer">
            <span>Thoughtful assistance. Human decisions.</span>
            <span>
              {workspace
                ? "Owner review workspace"
                : page === "test-email"
                  ? "Fictional data · Live AI"
                  : (page === "tour" &&
                        new URLSearchParams(location.search).get("mode") !==
                          "recorded") ||
                      (page === "reviews" &&
                        ((!id && !location.search) || id?.startsWith("live-")))
                    ? "Fictional data · Live AI · Simulated booking"
                    : "Fictional data · Predefined examples"}
              <span className="footer-dot">·</span>Australia / Melbourne
            </span>
          </footer>
        </div>
      </div>
    </Context.Provider>
  );
}

function Overview() {
  const { workspace, base } = useSite();
  const { value, error, loading, refresh } = useLoad(async () => {
    const [runs, students, pending] = await Promise.all([
      get<Page<RunSummary>>(workspace, "/agent-runs", { limit: 4 }),
      get<Page<Student>>(workspace, "/students", { limit: 1 }),
      get<Page<RunSummary>>(workspace, "/agent-runs", {
        status: "awaiting_review",
        limit: 1,
      }),
    ]);
    return { runs, students, pending };
  }, [workspace]);
  if (!workspace) {
    const exampleSessions = examples.class_sessions
      .filter((session) => session.starts_at.slice(0, 10) >= examples.as_of)
      .slice()
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
      .slice(0, 2);
    return (
      <>
        <PageHeader
          eyebrow="PUBLIC DEMO · FICTIONAL DATA"
          title="AI support for every enquiry."
        >
          From a student’s email to a draft ready for your review.
        </PageHeader>
        <section className="ai-workflow" aria-labelledby="ai-workflow-title">
          <div className="ai-workflow-heading">
            <span className="ai-workflow-sparkle">
              <Sparkles size={19} aria-hidden="true" />
            </span>
            <div>
              <span className="eyebrow">YOUR AI COPILOT</span>
              <h2 id="ai-workflow-title">From enquiry to response</h2>
            </div>
          </div>
          <ol className="ai-workflow-steps">
            <li>
              <span className="ai-step-icon">
                <Mail size={18} aria-hidden="true" />
              </span>
              <div>
                <strong>Student enquiry</strong>
                <span>Read the conversation</span>
              </div>
            </li>
            <li className="ai-step-highlight">
              <span className="ai-step-icon">
                <Sparkles size={18} aria-hidden="true" />
              </span>
              <div>
                <strong>AI-assisted draft</strong>
                <span>Uses example studio context</span>
              </div>
            </li>
            <li>
              <span className="ai-step-icon">
                <ClipboardCheck size={18} aria-hidden="true" />
              </span>
              <div>
                <strong>Teacher review</strong>
                <span>You make the decision</span>
              </div>
            </li>
          </ol>
        </section>
        <div className="overview-dashboard">
          <section
            className="panel overview-enquiries"
            aria-labelledby="overview-enquiries-title"
          >
            <div className="section-heading">
              <div>
                <div className="eyebrow">FICTIONAL EXAMPLES</div>
                <h2 id="overview-enquiries-title">Choose an enquiry</h2>
              </div>
              <Link className="inline-link" to={`${base}/reviews`}>
                View queue <ArrowRight size={16} />
              </Link>
            </div>
            <LiveReviewCases dashboard />
          </section>
          <aside
            className="overview-dashboard-side"
            aria-label="Studio overview"
          >
            <section
              className="panel dashboard-timetable"
              aria-labelledby="dashboard-timetable-title"
            >
              <div className="section-heading">
                <div>
                  <div className="eyebrow">EXAMPLE SCHEDULE</div>
                  <h2 id="dashboard-timetable-title">Classes</h2>
                </div>
                <CalendarDays size={20} aria-hidden="true" />
              </div>
              <p className="dashboard-snapshot">
                Example snapshot · {dateLabel(examples.as_of)}
              </p>
              {exampleSessions.map((session) => {
                const cls = examples.classes.find(
                  (item) => item.id === session.class_id,
                );
                const location = examples.locations.find(
                  (item) => item.id === cls?.location_id,
                );
                return (
                  <div className="dashboard-session" key={session.id}>
                    <strong>{cls?.name ?? "Class"}</strong>
                    <span>{timeLabel(session.starts_at)}</span>
                    {location && <span>{location.name}</span>}
                  </div>
                );
              })}
              <Link className="inline-link" to={`${base}/timetable`}>
                View timetable <ArrowRight size={16} />
              </Link>
            </section>
            <section
              className="panel dashboard-shortcuts"
              aria-labelledby="dashboard-shortcuts-title"
            >
              <div className="section-heading">
                <h2 id="dashboard-shortcuts-title">Studio resources</h2>
                <BookOpen size={20} aria-hidden="true" />
              </div>
              <Link to={`${base}/knowledge/rules`}>
                <span>Studio rules</span>
                <ArrowUpRight size={16} />
              </Link>
              <Link to={`${base}/students`}>
                <span>Student records</span>
                <ArrowUpRight size={16} />
              </Link>
            </section>
          </aside>
        </div>
        <div className="example-footnote">
          <CircleHelp size={16} />
          <p>
            Fictional examples. Generate a response to review; no email is sent.
          </p>
        </div>
      </>
    );
  }
  return (
    <>
      <PageHeader eyebrow="AT A GLANCE" title="Your studio, in view.">
        Review enquiries with the conversation and studio context beside you.
      </PageHeader>
      <section className="hero panel">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="availability-dot" />
            READY FOR HUMAN REVIEW
          </div>
          <h2>Every email has a story behind it.</h2>
          <p>
            The copilot connects the conversation, student history, and class
            timetable to prepare a draft for a teacher to review.
          </p>
          <Link className="button primary" to={`${base}/reviews`}>
            Open review queue <ArrowRight size={17} />
          </Link>
          <span className="hero-caption">
            Approval books a proposed session and saves the response.
          </span>
        </div>
        <div
          className="hero-visual"
          aria-label="An email becomes a contextual draft for teacher review"
        >
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="floating-note note-email">
            <span className="visual-icon">
              <Mail size={18} />
            </span>
            <div>
              <small>INCOMING EMAIL</small>
              <strong>
                “Actually, Saturday
                <br />
                would be better.”
              </strong>
            </div>
            <span className="note-counter">01</span>
          </div>
          <div className="visual-connector">
            <ArrowDown size={23} />
          </div>
          <div className="floating-note note-context">
            <span className="visual-icon">
              <GitBranch size={18} />
            </span>
            <div>
              <small>CONTEXT CONNECTED</small>
              <strong>History. Memory. Timetable.</strong>
            </div>
            <Check size={17} />
          </div>
          <div className="floating-note note-draft">
            <span className="visual-icon">
              <FileText size={18} />
            </span>
            <div>
              <small>A DRAFT, WITH REASONS</small>
              <strong>Ready for a human perspective.</strong>
            </div>
            <span className="draft-dot" />
          </div>
          <div className="visual-footnote">
            <Sparkles size={13} />
            Assist the judgement. Keep the human.
          </div>
        </div>
      </section>
      <div className="metric-grid">
        <Metric
          value={value?.pending.total}
          label="Awaiting review"
          note="Drafts ready for your attention"
          icon={<Mail size={20} />}
        />
        <Metric
          value={value?.students.total}
          label="Student profiles"
          note="History and source-linked context"
          icon={<Users size={20} />}
        />
      </div>
      <ErrorBox error={error} retry={refresh} />
      <section className="panel">
        <div className="section-heading">
          <div>
            <div className="eyebrow">THE CONVERSATION CONTINUES</div>
            <h2>Recent enquiries</h2>
          </div>
          <Link className="inline-link" to={`${base}/reviews`}>
            View all <ArrowRight size={16} />
          </Link>
        </div>
        {loading && !value ? (
          <Loading />
        ) : (
          value && <RunRows runs={value.runs.items} showEmailFallback />
        )}
      </section>
    </>
  );
}

function Metric({
  value,
  label,
  note,
  icon,
}: {
  value?: number;
  label: string;
  note: string;
  icon: ReactNode;
}) {
  return (
    <div className="metric panel">
      <div className="metric-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value ?? "—"}</strong>
      <small>{note}</small>
    </div>
  );
}
function RunRows({
  runs,
  showEmailFallback = false,
}: {
  runs: RunSummary[];
  showEmailFallback?: boolean;
}) {
  const { base } = useSite();
  if (!runs.length) return <Empty>No enquiries match this view.</Empty>;
  return (
    <div className="run-list">
      {runs.map((run) => (
        <Link className="run-row" key={run.id} to={`${base}/reviews/${run.id}`}>
          <span className="avatar">
            {run.student_name
              .split(" ")
              .map((part) => part[0])
              .slice(0, 2)
              .join("")}
          </span>
          <div className="run-person">
            <strong>{run.student_name}</strong>
            {run.request_summary && (
              <span className="case-description">{run.request_summary}</span>
            )}
            {showEmailFallback && !run.request_summary && (
              <span>{run.student_email}</span>
            )}
            <IntentBadges routing={run.routing} />
          </div>
          <div className="run-meta">
            <Status status={run.status} />
            <small>{dateLabel(run.created_at)}</small>
          </div>
          <ArrowUpRight className="row-arrow" size={17} />
        </Link>
      ))}
    </div>
  );
}
function ReviewQueue() {
  const { workspace } = useSite();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "",
    status = params.get("status") || "",
    offset = Number(params.get("offset") || 0);
  const { value, error, loading, refresh } = useLoad(
    () =>
      get<Page<RunSummary>>(workspace, "/agent-runs", {
        q,
        status,
        offset,
        limit: 10,
        student_id: params.get("student_id") || undefined,
        conversation_id: params.get("conversation_id") || undefined,
      }),
    [workspace, params.toString()],
  );
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("offset");
    setParams(next);
  }
  return (
    <>
      <PageHeader
        eyebrow="EMAILS → CONTEXT → DRAFTS"
        title="The review queue."
        action={
          <button className="button secondary" onClick={refresh}>
            <RefreshCw size={16} />
            Refresh
          </button>
        }
      >
        Open an enquiry to see the story, evidence, and response together.
      </PageHeader>
      <div className="panel">
        <div className="filters">
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search enquiries"
              placeholder="Search student name or email"
              value={q}
              onChange={(event) => filter("q", event.target.value)}
            />
          </label>
          <label className="select-field">
            <span>Status</span>
            <select
              aria-label="Filter by status"
              value={status}
              onChange={(event) => filter("status", event.target.value)}
            >
              <option value="">All statuses</option>
              {statuses.map((state) => (
                <option key={state} value={state}>
                  {statusLabel[state]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <ErrorBox error={error} retry={refresh} />
        {loading ? (
          <Loading />
        ) : (
          value && (
            <>
              <RunRows runs={value.items} />
              <Pager
                page={value}
                onChange={(offset) => {
                  const next = new URLSearchParams(params);
                  next.set("offset", String(offset));
                  setParams(next);
                }}
              />
            </>
          )
        )}
      </div>
      {!workspace && (
        <p className="muted footnote">
          These predefined examples include a correction, missing details, a
          teacher handoff, a reviewed response, and a recoverable failure.
        </p>
      )}
    </>
  );
}

function ConversationMessage({
  message,
  studentName,
}: {
  message: Message;
  studentName: string;
}) {
  return (
    <article
      id={`message-${message.id}`}
      className={`message message-${message.kind}`}
    >
      <div className="message-meta">
        <strong>
          {message.kind === "student_email"
            ? studentName
            : message.kind === "teacher_response"
              ? "Reviewed response"
              : message.kind === "assistant_draft"
                ? "Generated draft"
                : "Staff note"}
        </strong>
        <small>{timeLabel(message.occurred_at)}</small>
      </div>
      <p>{message.body}</p>
    </article>
  );
}
function ReviewDetail({ id }: { id: string }) {
  const { workspace, base, identity } = useSite();
  const [draft, setDraft] = useState(""),
    [feedback, setFeedback] = useState("");
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [actionError, setActionError] = useState<Error>();
  const [message, setMessage] = useState("");
  const [confirmReplaceEdits, setConfirmReplaceEdits] = useState(false);
  const [revisionKind, setRevisionKind] = useState<"revise" | "regenerate">(
    "revise",
  );
  const [resolutionEdits, setResolutionEdits] = useState<
    Record<string, QuestionResolution>
  >({});
  const revision = useRef(-1);
  const historyRef = useRef<HTMLDetailsElement>(null);
  const [pollingStatus, setPollingStatus] = useState<RunStatus>();
  const state = useLoad(
    async () => {
      const run = await get<Run>(workspace, `/agent-runs/${id}`);
      const conversation = await get<Conversation>(
        workspace,
        `/conversations/${run.conversation_id}`,
      );
      const [student, messages, classes, sessions, locations, terms] =
        await Promise.all([
          get<StudentDetail>(workspace, `/students/${conversation.student_id}`),
          all<Message>(workspace, `/conversations/${conversation.id}/messages`),
          all<StudioClass>(workspace, "/classes"),
          all<Session>(workspace, "/sessions"),
          all<Location>(workspace, "/locations"),
          all<Term>(workspace, "/terms"),
        ]);
      return {
        run,
        conversation,
        student,
        messages,
        classes,
        sessions,
        locations,
        terms,
      };
    },
    [workspace, id],
    workspace && ["running", "finalizing"].includes(pollingStatus || "")
      ? 5000
      : undefined,
  );
  const { value } = state;
  useEffect(() => {
    if (!value) return;
    setPollingStatus(value.run.status);
    if (revision.current === -1 || !dirty) {
      setDraft(value.run.draft_details.body || "");
      revision.current = value.run.revision;
    }
  }, [value]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (dirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  const blocker = useBlocker(dirty);
  async function action(
    action: "approve" | "revise" | "regenerate" | "reject" | "retry",
  ) {
    if (!value || busy) return;
    setBusy(true);
    setActionError(undefined);
    setMessage("");
    try {
      const result = await post<Run>(
        `/api/v1/agent-runs/${id}/${action === "retry" ? "retry" : "review"}`,
        identity.csrf_token || "",
        action === "retry"
          ? undefined
          : {
              action: action === "regenerate" ? "revise" : action,
              expected_revision: revision.current,
              ...(action === "approve"
                ? { body: draft }
                : action === "revise" || action === "regenerate"
                  ? {
                      ...(action === "regenerate" ? { regenerate: true } : {}),
                      ...(feedback.trim() ? { feedback } : {}),
                      ...(Object.keys(resolutionEdits).length
                        ? {
                            question_resolutions:
                              Object.values(resolutionEdits),
                          }
                        : {}),
                      ...(action === "revise" &&
                      !feedback.trim() &&
                      !Object.keys(resolutionEdits).length
                        ? {
                            feedback:
                              "Regenerate the question checklist for this older review.",
                          }
                        : {}),
                    }
                  : {}),
            },
      );
      window.dispatchEvent(new Event("review-queue-changed"));
      setPollingStatus(result.status);
      if (result.status !== "failed") {
        const applied = result.draft_details.question_resolutions || [];
        const choicesApplied = Object.values(resolutionEdits).every((choice) =>
          applied.some(
            (item) =>
              item.question_id === choice.question_id &&
              item.decision === choice.decision &&
              item.answer === choice.answer,
          ),
        );
        if (action !== "retry" || choicesApplied) {
          setDirty(false);
          setFeedback("");
          setResolutionEdits({});
        }
        setDraft(result.draft_details.body || "");
        revision.current = result.revision;
      }
      setMessage(
        result.status === "approved"
          ? result.draft_details.booking_session_id
            ? "Class booked and response saved. No email has been sent."
            : "Response approved and saved. No email has been sent."
          : result.status === "failed"
            ? "The run needs attention. Inspect its current state before retrying."
            : result.status === "finalizing"
              ? "The response is stored. Student memory is still being reconciled."
              : action === "revise" || action === "regenerate"
                ? "A new draft revision is ready."
                : action === "reject"
                  ? "Review closed without approving a response."
                  : "Run refreshed.",
      );
      state.refresh();
    } catch (err) {
      setActionError(err as Error);
      state.refresh();
    } finally {
      setBusy(false);
    }
  }
  if (!value)
    return (
      <>
        <ErrorBox error={state.error} retry={state.refresh} />
        {state.loading && <Loading />}
      </>
    );
  const { run, student, messages, classes } = value;
  const canReview = workspace && run.status === "awaiting_review";
  const missingDecisions = missingTeacherDecisions(run);
  const pendingChoices = Object.keys(resolutionEdits).length > 0;
  const pendingInvalid = Object.values(resolutionEdits).some(
    (choice) => choice.decision === "answer" && !choice.answer?.trim(),
  );
  const legacyQuestions = missingDecisions.some(
    (answer) => !answer.question_id,
  );
  const enquiryReview =
    run.interpretation.flow !== "makeup" && !!run.draft_details.answers?.length;
  const retryable =
    workspace &&
    ["failed", "running", "finalizing"].includes(run.status) &&
    (run.approved_response_id ||
      run.draft_details.failure_code !== "question_limit_exceeded");
  const canCloseFailed =
    workspace && run.status === "failed" && !run.approved_response_id;
  const missing = Array.isArray(run.interpretation.missing_details)
    ? (run.interpretation.missing_details as string[])
    : [];
  const approved = messages.find((row) => row.id === run.approved_response_id);
  const proposal = run.draft_details.booking_session_id;
  const booked =
    !!run.approved_response_id &&
    value.sessions.some(
      (session) =>
        session.id === proposal && session.students.includes(student.id),
    );
  const bookingSession = value.sessions.find((row) => row.id === proposal);
  const bookingClass = classes.find(
    (row) => row.id === bookingSession?.class_id,
  );
  const bookingLocation = value.locations.find(
    (row) => row.id === bookingClass?.location_id,
  );
  const sourceMessage = messages.find(
    (row) => row.id === run.source_message_id,
  );
  const historyCount = messages.filter(
    (row) => row.id !== run.source_message_id,
  ).length;
  const requestedActions = Array.isArray(run.interpretation.requested_actions)
    ? run.interpretation.requested_actions.filter(
        (action): action is string => typeof action === "string",
      )
    : [];
  const citedDocuments = new Map<string, Record<string, unknown>>();
  for (const item of run.evidence) {
    if (item.tool !== "document_answer") continue;
    for (const citation of documentCitations(item.result)) {
      if (typeof citation.evidence_id === "string")
        citedDocuments.set(citation.evidence_id, citation);
    }
  }
  const references: {
    raw: string;
    label: string;
    to?: string;
    messageId?: string;
  }[] = (run.draft_details.references || []).map((raw) => {
    const message = messages.find((item) => item.id === raw);
    if (message)
      return {
        raw,
        label:
          message.id === run.source_message_id
            ? "Student request"
            : `Conversation message · ${timeLabel(message.occurred_at)}`,
        messageId: message.id,
      };
    const separator = raw.indexOf(":");
    const kind = separator < 0 ? raw : raw.slice(0, separator);
    const id = separator < 0 ? "" : raw.slice(separator + 1);
    if (kind === "class") {
      const cls = classes.find((item) => item.id === id);
      return {
        raw,
        label: cls ? `Class: ${cls.name}` : "Class record unavailable",
        to: cls
          ? `${base}/timetable?class=${encodeURIComponent(id)}`
          : undefined,
      };
    }
    if (kind === "session") {
      const session = value.sessions.find((item) => item.id === id);
      const cls = classes.find((item) => item.id === session?.class_id);
      const location = value.locations.find(
        (item) => item.id === cls?.location_id,
      );
      return {
        raw,
        label: session
          ? `Session: ${cls?.name || "Class"} · ${timeLabel(session.starts_at, location?.timezone)}`
          : "Session record unavailable",
        to: session
          ? `${base}/timetable?session=${encodeURIComponent(id)}`
          : undefined,
      };
    }
    if (kind === "location") {
      const location = value.locations.find((item) => item.id === id);
      return {
        raw,
        label: location
          ? `Studio: ${location.name}`
          : "Studio record unavailable",
      };
    }
    if (kind === "term") {
      const term = value.terms.find((item) => item.id === id);
      return {
        raw,
        label: term ? `Term: ${term.name}` : "Term record unavailable",
      };
    }
    if (kind === "policy")
      return { raw, label: "Studio policy used for this draft" };
    if (kind === "document") {
      const citation = citedDocuments.get(id);
      return {
        raw,
        label: citation
          ? `${String(citation.title)} · Revision ${String(citation.revision)}`
          : `Document citation [${id}] · See supporting evidence`,
        to: workspace ? documentCitationUrl(citation) : undefined,
      };
    }
    if (kind === "teacher_answer" || kind === "teacher_deferral") {
      const question = run.draft_details.answers?.find(
        (answer) => answer.question_id === id,
      )?.question;
      return {
        raw,
        label: `${kind === "teacher_answer" ? "Teacher answer" : "Teacher deferral"}${question ? `: ${question}` : ""}`,
      };
    }
    if (raw === "teacher_feedback")
      return { raw, label: "Teacher revision instruction" };
    return { raw, label: "Other supporting record" };
  });
  const draftEditsPending =
    canReview && draft !== (run.draft_details.body || "");
  function requestRevision(kind: "revise" | "regenerate") {
    if (draftEditsPending) {
      setRevisionKind(kind);
      setConfirmReplaceEdits(true);
      return;
    }
    void action(kind);
  }
  const approvalBlockedReason = busy
    ? "A review action is in progress."
    : legacyQuestions
      ? "Update this older draft to generate individual teacher questions."
      : pendingInvalid
        ? "Finish each teacher decision before updating the draft."
        : pendingChoices || !!feedback.trim()
          ? "Update the draft to apply your decisions or feedback."
          : missingDecisions.length > 0
            ? `Answer ${missingDecisions.length} teacher ${missingDecisions.length === 1 ? "question" : "questions"}, then update the draft.`
            : !draft.trim()
              ? "Write a final response before approving."
              : proposal && !bookingSession
                ? "The proposed session is unavailable. Request a revision."
                : undefined;
  return (
    <>
      <PageHeader
        eyebrow={workspace ? "OWNER REVIEW" : "AN EXAMPLE ENQUIRY"}
        title={value.conversation.subject || "Conversation review"}
        action={<Status status={run.status} />}
      >
        {summary(run)}
      </PageHeader>
      {blocker.state === "blocked" && (
        <div className="dialog-overlay">
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="unsaved-title"
            className="panel dialog"
          >
            <h2 id="unsaved-title">Keep your edits?</h2>
            <p>
              Your response has unsaved edits. Stay to continue, or leave and
              discard them.
            </p>
            <div className="button-row">
              <button
                autoFocus
                className="button primary"
                onClick={() => blocker.reset()}
              >
                Stay here
              </button>
              <button
                className="button secondary"
                onClick={() => blocker.proceed()}
              >
                Leave page
              </button>
            </div>
          </div>
        </div>
      )}
      {confirmReplaceEdits && (
        <div className="dialog-overlay">
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="replace-draft-title"
            className="panel dialog"
          >
            <h2 id="replace-draft-title">Replace your text edits?</h2>
            <p>
              {revisionKind === "regenerate"
                ? "Regenerating will replace the response text you edited. Your teacher answers and change prompt will be sent to the copilot."
                : "Updating the draft will replace the response text you edited. Your teacher answers and change prompt will be sent to the copilot."}
            </p>
            <div className="button-row">
              <button
                autoFocus
                className="button secondary"
                onClick={() => setConfirmReplaceEdits(false)}
              >
                Keep editing
              </button>
              <button
                className="button primary"
                onClick={() => {
                  setConfirmReplaceEdits(false);
                  void action(revisionKind);
                }}
              >
                {revisionKind === "regenerate"
                  ? "Replace and regenerate response"
                  : "Replace and update draft"}
              </button>
            </div>
          </div>
        </div>
      )}
      <ErrorBox error={state.error} retry={state.refresh} />
      <ErrorBox error={actionError} />
      {actionError instanceof ApiError && actionError.status === 409 && (
        <div className="notice">
          This review changed elsewhere. Your text is preserved.{" "}
          <button
            className="text-button"
            onClick={() => {
              setDirty(false);
              revision.current = run.revision;
              setDraft(run.draft_details.body || "");
              setFeedback("");
              setResolutionEdits({});
              setActionError(undefined);
            }}
          >
            Load the latest draft and discard local edits
          </button>
        </div>
      )}
      {message && (
        <div className="notice success" role="status">
          {message}
        </div>
      )}
      {run.error && (
        <div className="notice error">
          <strong>
            {run.approved_response_id
              ? "Response saved; memory update needs recovery."
              : "Processing needs attention."}
          </strong>
          <p>{run.error}</p>
        </div>
      )}
      {!workspace && (
        <div className="demo-notice">
          <BookOpen size={17} />
          <span>
            Read-only example. Drafts and review outcomes here are predefined
            illustrations.
          </span>
        </div>
      )}
      <div className="review-flow">
        <section className="panel conversation-panel review-request">
          <div className="section-heading compact">
            <div>
              <div className="eyebrow">STUDENT REQUEST</div>
              <h2>What the student asked</h2>
            </div>
            <Mail size={17} />
          </div>
          {sourceMessage ? (
            <article
              id={`message-${sourceMessage.id}`}
              className={`message message-${sourceMessage.kind} source-message`}
            >
              <div className="message-meta">
                <strong>{student.display_name}</strong>
                <span className="review-email-address">{student.email}</span>
                <small>{timeLabel(sourceMessage.occurred_at)}</small>
              </div>
              <p>{sourceMessage.body}</p>
            </article>
          ) : (
            <p className="muted">
              The source email is unavailable. Inspect the conversation history
              below.
            </p>
          )}
        </section>
        <section className="panel review-main" id="review-response">
          <div className="section-heading compact">
            <div>
              <div className="eyebrow">
                {approved
                  ? "SAVED RESPONSE"
                  : `CURRENT RESPONSE · REVISION ${run.revision}`}
              </div>
              <h2>{approved ? "Saved response" : "Current response"}</h2>
            </div>
            <FileText size={18} />
          </div>
          {canReview && !!run.draft_details.review_concerns?.length && (
            <section
              className="review-concerns"
              aria-labelledby="review-concerns-heading"
            >
              <h3 id="review-concerns-heading">Points to review</h3>
              <p>Check these points before approving the response.</p>
              <ul>
                {run.draft_details.review_concerns.map((concern, index) => (
                  <li key={index}>{concern}</li>
                ))}
              </ul>
            </section>
          )}
          {approved ? (
            <>
              <div className="saved-response prose">{approved.body}</div>
              <p className="muted footnote">
                <Check size={14} />
                Saved teacher response. Delivery is unconfirmed.
              </p>
            </>
          ) : canReview ? (
            <div className="editor-label">
              <label htmlFor="final-response">Final response</label>
              <textarea
                id="final-response"
                aria-label="Final response"
                maxLength={20000}
                value={draft}
                onChange={(event) => {
                  setDraft(event.target.value);
                  setDirty(true);
                }}
                disabled={busy}
                rows={13}
              />
              <small>
                {draftEditsPending
                  ? "Your wording edits are saved when you approve. Updating the draft will ask before replacing them."
                  : "Edit the wording here, or ask the copilot to change it below."}
              </small>
              <button
                className="button secondary"
                disabled={busy || pendingInvalid}
                onClick={() => requestRevision("regenerate")}
              >
                <RefreshCw size={14} />
                Regenerate response
              </button>
            </div>
          ) : (
            <div className="saved-response prose">
              {run.draft_details.body ||
                "No draft was produced. The run can be inspected and recovered by the owner."}
            </div>
          )}
          {(proposal || booked) && (
            <BookingProposal
              booked={Boolean(booked)}
              className={bookingClass?.name || "Session unavailable"}
              startsAt={bookingSession?.starts_at}
              timezone={bookingLocation?.timezone}
              location={bookingLocation?.name}
              sessionUrl={
                bookingSession
                  ? `${base}/timetable?session=${bookingSession.id}`
                  : undefined
              }
            />
          )}
          {!!run.draft_details.answers?.length && (
            <EnquiryPanel
              run={run}
              editable={canReview}
              busy={busy}
              edits={resolutionEdits}
              onChange={(choice) => {
                setResolutionEdits((previous) => ({
                  ...previous,
                  [choice.question_id]: choice,
                }));
                setDirty(true);
              }}
            />
          )}
          {canReview && (
            <div className="review-revision" id="review-revision">
              <h3>Change this response</h3>
              <label>
                What should the copilot change?
                <textarea
                  aria-label="Change prompt"
                  value={feedback}
                  maxLength={4000}
                  onChange={(event) => {
                    setFeedback(event.target.value);
                    setDirty(true);
                  }}
                  placeholder="For example, make the answer shorter or explain the next class."
                  rows={3}
                  disabled={busy}
                />
              </label>
              <button
                className="button secondary"
                disabled={
                  busy ||
                  pendingInvalid ||
                  (!feedback.trim() && !pendingChoices && !legacyQuestions)
                }
                onClick={() => requestRevision("revise")}
              >
                <RefreshCw size={14} />
                Update draft
              </button>
              <p className="muted footnote">
                The updated response replaces the draft above. You can repeat
                this as often as needed before approval.
              </p>
            </div>
          )}
          {canReview && (
            <div className="review-actions">
              <button
                className="button primary full-width"
                disabled={
                  busy ||
                  !draft.trim() ||
                  (!!proposal && !bookingSession) ||
                  missingDecisions.length > 0 ||
                  pendingChoices ||
                  !!feedback.trim()
                }
                onClick={() => action("approve")}
              >
                <Check size={17} />
                {busy
                  ? "Processing…"
                  : proposal
                    ? "Approve and book class"
                    : "Approve and save response"}
              </button>
              <p className="muted footnote">
                {proposal
                  ? "Books the proposed session and saves your response together. No email is sent."
                  : "Saves your response. No booking is proposed and no email is sent."}
              </p>
              {approvalBlockedReason && (
                <p className="approval-guidance" role="status">
                  Approval unavailable: {approvalBlockedReason}
                </p>
              )}
              <button
                className="text-button danger"
                disabled={busy}
                onClick={() => action("reject")}
              >
                Close review
              </button>
            </div>
          )}
          {(run.status === "running" || run.status === "finalizing") && (
            <p className="muted">
              {run.status === "finalizing"
                ? "The response is stored while student memory is reconciled."
                : "The draft is still being prepared."}
            </p>
          )}
          {(run.status === "closed" || run.status === "superseded") && (
            <p className="muted">
              There are no actions available for this review.
            </p>
          )}
          {(retryable || canCloseFailed) && (
            <div className="review-recovery">
              <h3>Recover this review</h3>
              {retryable && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => action("retry")}
                >
                  <RefreshCw size={15} />
                  {busy ? "Processing…" : "Retry this run"}
                </button>
              )}
              {canCloseFailed && (
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => action("reject")}
                >
                  Close review
                </button>
              )}
            </div>
          )}
          {!workspace && (
            <div className="review-explanation">
              <ShieldCheck size={18} />
              <p>
                {proposal
                  ? "In the owner workspace, a teacher can edit or update this draft, then approve a booking and save the response."
                  : "In the owner workspace, a teacher can edit or update this draft, then approve and save the response."}{" "}
                Approval does not send an email.
              </p>
            </div>
          )}
        </section>
        {historyCount > 0 && (
          <details className="panel conversation-history" ref={historyRef}>
            <summary>
              Conversation history · {historyCount}
              {historyCount === 1 ? " message" : " messages"}
            </summary>
            <div className="thread">
              {messages
                .filter((row) => row.id !== run.source_message_id)
                .map((row) => (
                  <ConversationMessage
                    key={row.id}
                    message={row}
                    studentName={student.display_name}
                  />
                ))}
            </div>
          </details>
        )}
        {(missing.length > 0 ||
          requestedActions.length > 0 ||
          run.draft_details.rationale ||
          references.length > 0) && (
          <details className="panel response-support">
            <summary>Response notes and references</summary>
            {requestedActions.length > 0 && (
              <div className="enquiry-actions">
                <h3>Actions for the teacher</h3>
                <ul>
                  {requestedActions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
                <p className="muted">
                  These actions have not been performed. Approval saves the
                  reply only.
                </p>
              </div>
            )}
            {missing.length > 0 && (
              <div className="notice">
                <strong>Information still needed</strong>
                <ul>
                  {missing.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {run.draft_details.rationale && (
              <div className="rationale">
                <span className="eyebrow">WHY THIS RESPONSE</span>
                <p>{run.draft_details.rationale}</p>
              </div>
            )}
            {references.length > 0 && (
              <div className="source-links">
                <span className="eyebrow">REFERENCES</span>
                {references.map((reference) =>
                  reference.messageId ? (
                    <a
                      href={`#message-${reference.messageId}`}
                      key={reference.raw}
                      onClick={() => {
                        if (
                          reference.messageId !== run.source_message_id &&
                          historyRef.current
                        )
                          historyRef.current.open = true;
                      }}
                    >
                      {reference.label} <ArrowUpRight size={12} />
                    </a>
                  ) : reference.to ? (
                    <Link to={reference.to} key={reference.raw}>
                      {reference.label} <ArrowUpRight size={12} />
                    </Link>
                  ) : (
                    <span key={reference.raw}>{reference.label}</span>
                  ),
                )}
              </div>
            )}
          </details>
        )}
        <details className="panel review-support">
          <summary>Student, classification and supporting evidence</summary>
          <div className="support-content">
            <ClassificationPanel
              interpretation={run.interpretation}
              status={run.status}
            />
            <section className="panel context-card">
              <div className="eyebrow">THE STUDENT</div>
              <Link
                className="student-heading"
                to={`${base}/students/${student.id}`}
              >
                <span className="avatar">{student.display_name[0]}</span>
                <div>
                  <h3>{student.display_name}</h3>
                  <small>
                    {student.highest_level || "Level not yet known"}
                  </small>
                </div>
                <ArrowUpRight size={15} />
              </Link>
              <dl>
                <dt>Email</dt>
                <dd>{student.email}</dd>
                <dt>Current enrolments</dt>
                <dd>
                  {student.current_enrolments.length
                    ? student.current_enrolments.map((row) => (
                        <div key={row.id}>
                          {classes.find((cls) => cls.id === row.class_id)
                            ?.name || row.class_id}
                        </div>
                      ))
                    : "None on this date"}
                </dd>
              </dl>
              <span className="eyebrow">CONVERSATION MEMORY</span>
              <p>{student.ai_summary || "No summary available."}</p>
              <small className="muted">
                Memory provides context. Official enrolments remain
                authoritative.
              </small>
            </section>
            <section className="panel context-card">
              <div className="eyebrow">SUPPORTING EVIDENCE</div>
              {run.evidence.length ? (
                run.evidence.map((item, index) => (
                  <div className="evidence" key={index}>
                    <span className="evidence-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <p>
                      {typeof item.finding === "string"
                        ? item.finding
                        : typeof item.tool === "string"
                          ? item.tool
                          : "Tool result"}
                    </p>
                    {typeof item.session_id === "string" && (
                      <Link
                        className="inline-link"
                        to={`${base}/timetable?session=${encodeURIComponent(item.session_id)}`}
                      >
                        View session <ArrowUpRight size={13} />
                      </Link>
                    )}
                    {item.tool === "document_answer" && (
                      <DocumentAnswerEvidence
                        result={item.result}
                        workspace={workspace}
                      />
                    )}
                    <details>
                      <summary>Inspect result</summary>
                      <Json value={item} />
                    </details>
                  </div>
                ))
              ) : (
                <p className="muted">
                  No supporting evidence was collected for this run.
                </p>
              )}
            </section>
          </div>
        </details>
      </div>
      <details className="panel developer-panel">
        <summary>
          <GitBranch size={17} />
          Developer details · run state and policy
        </summary>
        <div className="developer-grid">
          <div>
            <h3>Run identity</h3>
            <dl>
              <dt>Run ID</dt>
              <dd className="mono">{run.id}</dd>
              <dt>Source message</dt>
              <dd className="mono">{run.source_message_id}</dd>
              <dt>Status / revision</dt>
              <dd>
                {run.status} / {run.revision}
              </dd>
            </dl>
            <h3>Policy snapshot</h3>
            <Json value={run.policy_snapshot} />
          </div>
          <div>
            <h3>Interpretation</h3>
            <Json value={run.interpretation} />
            <h3>Draft reference IDs</h3>
            <Json value={run.draft_details.references || []} />
          </div>
        </div>
      </details>
    </>
  );
}

function Students() {
  const { workspace, base } = useSite();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "",
    offset = Number(params.get("offset") || 0);
  const { value, error, loading, refresh } = useLoad(
    () => get<Page<Student>>(workspace, "/students", { q, offset, limit: 10 }),
    [workspace, q, offset],
  );
  return (
    <>
      <PageHeader eyebrow="PEOPLE, WITH CONTEXT" title="Student stories.">
        Profiles connect official enrolments with the conversations around them.
      </PageHeader>
      <div className="panel filters timetable-filters student-filters">
        <div className="timetable-filter-title">
          <strong>Find a student</strong>
          <span>Search by name or email</span>
        </div>
        <label className="student-search-label">
          <span>Student</span>
          <span className="search-field">
            <Search size={17} aria-hidden="true" />
            <input
              aria-label="Search students"
              placeholder="Search by name or email"
              value={q}
              onChange={(event) =>
                setParams(event.target.value ? { q: event.target.value } : {})
              }
            />
          </span>
        </label>
      </div>
      <ErrorBox error={error} retry={refresh} />
      {loading ? (
        <Loading />
      ) : (
        value && (
          <>
            <div className="timetable-section-heading">
              <h2>Students</h2>
              <span>
                {value.total} {value.total === 1 ? "student" : "students"}
              </span>
            </div>
            {value.items.length ? (
              <div className="students-grid">
                {value.items.map((student) => (
                  <Link
                    className="panel student-card"
                    key={student.id}
                    to={`${base}/students/${student.id}`}
                  >
                    <div className="student-card-content">
                      <div className="student-card-header">
                        <span className="avatar" aria-hidden="true">
                          {student.display_name
                            .trim()
                            .split(/\s+/)
                            .map((word) => word[0])
                            .slice(0, 2)
                            .join("")
                            .toUpperCase()}
                        </span>
                        <h3>{student.display_name}</h3>
                      </div>
                      <div className="class-tags student-card-tags">
                        <span
                          className={
                            student.highest_level
                              ? "class-tag-level"
                              : "student-tag-unknown"
                          }
                        >
                          {student.highest_level || "Level not recorded"}
                        </span>
                      </div>
                      <div className="student-contact">
                        <span>Email</span>
                        <span>{student.email}</span>
                      </div>
                    </div>
                    <div className="student-card-footer">
                      <span>Student profile</span>
                      <span>
                        View profile <ArrowUpRight size={15} />
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="panel">
                <Empty>No students match this search.</Empty>
              </div>
            )}
            <Pager
              page={value}
              onChange={(offset) =>
                setParams({ ...(q ? { q } : {}), offset: String(offset) })
              }
            />
          </>
        )
      )}
    </>
  );
}
function StudentPage({ id }: { id: string }) {
  const { workspace, base } = useSite();
  const { value, error, loading, refresh } = useLoad(async () => {
    const [student, conversations, classes, sessions, locations, terms] =
      await Promise.all([
        get<StudentDetail>(
          workspace,
          `/students/${id}`,
          workspace ? {} : { on_date: examples.as_of },
        ),
        all<Conversation>(workspace, "/conversations", { student_id: id }),
        all<StudioClass>(workspace, "/classes"),
        all<Session>(workspace, "/sessions"),
        all<Location>(workspace, "/locations"),
        all<Term>(workspace, "/terms"),
      ]);
    const threads = await Promise.all(
      conversations.map(async (conversation) => ({
        conversation,
        messages: await all<Message>(
          workspace,
          `/conversations/${conversation.id}/messages`,
        ),
      })),
    );
    return {
      student,
      threads,
      classes,
      sessions,
      locations,
      terms,
    };
  }, [workspace, id]);
  return (
    <>
      <ErrorBox error={error} retry={refresh} />
      {loading ? (
        <Loading />
      ) : (
        value && (
          <>
            <PageHeader
              eyebrow="STUDENT PROFILE"
              title={value.student.display_name}
            >
              {value.student.email}{" "}
              <span className="profile-heading-level">
                {value.student.highest_level || "Level not recorded"}
              </span>
            </PageHeader>
            <div className="profile-grid">
              <section className="panel profile-card profile-enrolments">
                <div className="eyebrow">ENROLMENTS</div>
                <div className="section-heading">
                  <h2>Current enrolments</h2>
                </div>
                <p className="profile-card-description">
                  Ongoing class registrations
                </p>
                <Enrolments
                  rows={value.student.current_enrolments}
                  classes={value.classes}
                  locations={value.locations}
                />
                <details className="enrolment-history">
                  <summary>
                    <ChevronRight size={18} />
                    Full enrolment history
                  </summary>
                  <Enrolments
                    rows={value.student.enrolment_history}
                    classes={value.classes}
                    locations={value.locations}
                  />
                </details>
              </section>
              <section className="panel context-card profile-card profile-memory">
                <div className="eyebrow">CONVERSATION MEMORY</div>
                <h2>About this student</h2>
                <p className="profile-card-description">
                  Details and preferences shared in conversations
                </p>
                <StudentMemorySections
                  context={value.student.context}
                  summary={value.student.ai_summary}
                />
                <details>
                  <summary>Inspect stored context</summary>
                  <Json value={value.student.context} />
                </details>
              </section>
            </div>
            <section
              className="panel profile-card profile-sessions"
              aria-labelledby="confirmed-sessions-title"
            >
              <div className="eyebrow">SCHEDULE</div>
              <h2 id="confirmed-sessions-title">Confirmed sessions</h2>
              <p className="profile-card-description">
                Individual classes on the schedule
              </p>
              <ConfirmedSessionsList
                student={value.student}
                sessions={value.sessions}
                classes={value.classes}
                locations={value.locations}
              />
            </section>
            <section className="panel">
              <div className="section-heading">
                <h2>Conversations</h2>
              </div>
              {value.threads.length ? (
                value.threads.map(({ conversation, messages }) => (
                  <details
                    className="conversation-summary"
                    key={conversation.id}
                  >
                    <summary>
                      <span className="conversation-title">
                        {conversation.subject || "Untitled conversation"}
                      </span>
                      <span className="conversation-count">
                        {messages.length}{" "}
                        {messages.length === 1 ? "message" : "messages"}
                      </span>
                      <ChevronRight
                        className="conversation-chevron"
                        size={18}
                        aria-hidden="true"
                      />
                    </summary>
                    <ol
                      className="live-conversation profile-conversation"
                      aria-label="Conversation messages"
                    >
                      {messages.map((row) => {
                        const isStudent = row.kind === "student_email";
                        const sender = isStudent
                          ? value.student.display_name
                          : row.kind === "teacher_response"
                            ? "Reviewed response"
                            : row.kind === "assistant_draft"
                              ? "Generated draft"
                              : "Staff note";
                        const initials = isStudent
                          ? value.student.display_name
                              .trim()
                              .split(/\s+/)
                              .slice(0, 2)
                              .map((part) => part[0])
                              .join("")
                              .toUpperCase()
                          : row.kind === "assistant_draft"
                            ? "AI"
                            : "ST";
                        return (
                          <li
                            className={`live-conversation-message profile-message ${isStudent ? "profile-message-student" : "profile-message-response"}`}
                            key={row.id}
                          >
                            <span
                              className="live-conversation-avatar"
                              aria-hidden="true"
                            >
                              {initials}
                            </span>
                            <div className="live-conversation-content">
                              <div className="live-conversation-sender">
                                <strong>{sender}</strong>
                                <time dateTime={row.occurred_at}>
                                  {timeLabel(row.occurred_at)}
                                </time>
                              </div>
                              <div className="live-conversation-bubble">
                                {row.body}
                              </div>
                            </div>
                          </li>
                        );
                      })}
                    </ol>
                  </details>
                ))
              ) : (
                <Empty>No conversations have been recorded.</Empty>
              )}
            </section>
          </>
        )
      )}
    </>
  );
}
function StudentMemorySections({
  context,
  summary,
}: {
  context: Record<string, unknown>;
  summary: string | null;
}) {
  const memory = context._agent_memory;
  const record =
    memory && typeof memory === "object" && !Array.isArray(memory)
      ? (memory as Record<string, unknown>)
      : {};
  const requestMap =
    record.requests &&
    typeof record.requests === "object" &&
    !Array.isArray(record.requests)
      ? Object.values(record.requests)
      : [];
  const requests = requestMap.flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const entry = item as Record<string, unknown>;
    return typeof entry.request_summary === "string" &&
      entry.request_summary.trim()
      ? [
          {
            text: entry.request_summary,
            kind: entry.kind,
            approved: typeof entry.approved_response_id === "string",
          },
        ]
      : [];
  });
  if (
    !requests.length &&
    typeof record.request_summary === "string" &&
    record.request_summary.trim()
  )
    requests.push({
      text: record.request_summary,
      kind: undefined,
      approved: false,
    });
  const preferenceMap =
    record.preferences &&
    typeof record.preferences === "object" &&
    !Array.isArray(record.preferences)
      ? Object.values(record.preferences)
      : [];
  const preferences = preferenceMap.flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const value = (item as Record<string, unknown>).value;
    return typeof value === "string" && value.trim() ? [value] : [];
  });
  const hasStructuredRequests = requestMap.length > 0;
  const generatedSummary = summary?.startsWith(
    "Conversational memory; official student records remain authoritative.",
  );
  const requestsByConversation =
    record.requests &&
    typeof record.requests === "object" &&
    !Array.isArray(record.requests)
      ? (record.requests as Record<string, unknown>)
      : {};
  const approvedResponses =
    record.approved_responses &&
    typeof record.approved_responses === "object" &&
    !Array.isArray(record.approved_responses)
      ? Object.entries(record.approved_responses)
      : [];
  const earlierResponses = approvedResponses.flatMap(([id, item]) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const entry = item as Record<string, unknown>;
    const current =
      typeof entry.conversation_id === "string"
        ? requestsByConversation[entry.conversation_id]
        : undefined;
    const currentId =
      current && typeof current === "object" && !Array.isArray(current)
        ? (current as Record<string, unknown>).source_message_id
        : undefined;
    return currentId !== id &&
      typeof entry.request_summary === "string" &&
      entry.request_summary.trim()
      ? [entry.request_summary]
      : [];
  });
  return (
    <div className="profile-memory-content">
      <div className="profile-memory-activity">
        <span>Conversation summary</span>
        {hasStructuredRequests && generatedSummary ? (
          <p>
            {preferences.length
              ? preferences.join(" ")
              : "No ongoing preferences recorded yet."}
          </p>
        ) : (
          <p>{summary || "No conversation summary yet."}</p>
        )}
      </div>
      <div className="profile-memory-activity profile-request-summary">
        <span>Request summary</span>
        {requests.length ? (
          requests.map((request, index) => (
            <p key={index}>
              {request.text}
              {request.kind === "teacher_reviewed" ? " (Teacher reviewed)" : ""}
              {request.approved
                ? " Response approved; delivery unconfirmed."
                : ""}
            </p>
          ))
        ) : (
          <p>No requests recorded yet.</p>
        )}
      </div>
      {earlierResponses.length > 0 && (
        <div className="profile-memory-activity profile-request-summary">
          <span>Earlier teacher-approved responses</span>
          {earlierResponses.map((response, index) => (
            <p key={index}>{response} Delivery unconfirmed.</p>
          ))}
        </div>
      )}
      {hasStructuredRequests && generatedSummary && summary && (
        <details className="profile-full-summary">
          <summary>View full stored summary</summary>
          <p>{summary}</p>
        </details>
      )}
    </div>
  );
}
function classIdentity(cls: StudioClass | undefined, fallback: string) {
  if (!cls) return { title: fallback, weekday: undefined };
  const parts = cls.name.split(" · ").map((part) => part.trim());
  const weekday = parts.find((part) =>
    /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$/i.test(part),
  );
  const title =
    parts
      .filter(
        (part) =>
          part.toLowerCase() !== cls.level.trim().toLowerCase() &&
          part !== weekday,
      )
      .join(" · ") || cls.name;
  return { title, weekday };
}
function ProfileClassTags({
  cls,
  weekday,
  location,
  status,
}: {
  cls?: StudioClass;
  weekday?: string;
  location?: Location;
  status?: string;
}) {
  return (
    <div className="class-tags profile-class-tags">
      {cls?.level && <span className="class-tag-level">{cls.level}</span>}
      {weekday && <span className="class-tag-day">{weekday}</span>}
      {location && <span className="class-tag-location">{location.name}</span>}
      {status && (
        <span
          className={`profile-enrolment-status profile-enrolment-status-${status}`}
        >
          {status}
        </span>
      )}
    </div>
  );
}
function Enrolments({
  rows,
  classes,
  locations,
}: {
  rows: Enrolment[];
  classes: StudioClass[];
  locations: Location[];
}) {
  const { base } = useSite();
  return rows.length ? (
    <div className="enrolment-list">
      {rows.map((row) => {
        const cls = classes.find((item) => item.id === row.class_id);
        const location = locations.find((item) => item.id === cls?.location_id);
        const { title, weekday } = classIdentity(cls, row.class_id);
        return (
          <div className="profile-enrolment-item" key={row.id}>
            <Link
              className="profile-class-link"
              to={`${base}/timetable?class=${row.class_id}`}
            >
              {title}
              <ArrowUpRight size={14} />
            </Link>
            <ProfileClassTags cls={cls} status={row.status} />
            {(weekday || location) && (
              <p className="profile-class-location">
                {weekday && <span>{weekday}</span>}
                {weekday && location && " · "}
                {location && <span>{location.name}</span>}
              </p>
            )}
            <p className="profile-class-dates">
              {dateLabel(row.starts_on)} →{" "}
              {row.ends_on ? dateLabel(row.ends_on) : "Ongoing"}
            </p>
          </div>
        );
      })}
    </div>
  ) : (
    <p className="muted">No enrolments in this view.</p>
  );
}

function ConfirmedSessionsList({
  student,
  sessions,
  classes,
  locations,
}: {
  student: StudentDetail;
  sessions: Session[];
  classes: StudioClass[];
  locations: Location[];
}) {
  const { base } = useSite();
  const rows = confirmedSessions({
    studentId: student.id,
    sessions,
    classes,
    locations,
  });
  if (!rows.length) return <p className="muted">No confirmed sessions.</p>;
  return (
    <>
      <p className="profile-sessions-count">
        {rows.length} scheduled {rows.length === 1 ? "class" : "classes"}
      </p>
      <div className="confirmed-sessions-list">
        {rows.map(({ session, regularClass, location }) => {
          const { title } = classIdentity(regularClass, regularClass.name);
          const weekday = new Intl.DateTimeFormat("en-AU", {
            weekday: "long",
            timeZone: location.timezone,
          }).format(new Date(session.starts_at));
          return (
            <div className="enrolment confirmed-session" key={session.id}>
              <span className="profile-session-icon" aria-hidden="true">
                <CalendarDays size={18} />
              </span>
              <div className="profile-session-detail">
                <Link to={`${base}/timetable?session=${session.id}`}>
                  {title}
                  <ArrowUpRight size={14} />
                </Link>
                <ProfileClassTags
                  cls={regularClass}
                  weekday={weekday}
                  location={location}
                />
                <span>{timeLabel(session.starts_at, location.timezone)}</span>
                <div className="session-source-tags">
                  <span className="level-tag">Session student</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function Timetable() {
  const { workspace, base, identity } = useSite();
  const [attendanceError, setAttendanceError] = useState("");
  const [attendanceBusy, setAttendanceBusy] = useState(false);
  const [params, setParams] = useSearchParams();
  const [termFilter, setTermFilter] = useState(""),
    [locationFilter, setLocationFilter] = useState("");
  const classFilter = params.get("class") || "",
    selectedSession = params.get("session") || "";
  const state = useLoad(async () => {
    const [classes, sessions, terms, locations] = await Promise.all([
      all<StudioClass>(workspace, "/classes"),
      all<Session>(workspace, "/sessions"),
      all<Term>(workspace, "/terms"),
      all<Location>(workspace, "/locations"),
    ]);
    const roster = selectedSession
      ? await all<Student>(workspace, `/sessions/${selectedSession}/students`)
      : [];
    const attendance =
      workspace && selectedSession
        ? await get<Record<string, string>>(
            true,
            `/sessions/${selectedSession}/attendance`,
          )
        : {};
    return {
      classes,
      sessions,
      terms,
      locations,
      roster,
      attendance,
    };
  }, [workspace, selectedSession]);
  async function saveAttendance(studentId: string, status: string) {
    setAttendanceBusy(true);
    setAttendanceError("");
    try {
      await request(
        `/api/v1/sessions/${selectedSession}/attendance/${studentId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": identity.csrf_token || "",
          },
          body: JSON.stringify({ status }),
        },
      );
      state.refresh();
    } catch (error) {
      setAttendanceError((error as Error).message);
    } finally {
      setAttendanceBusy(false);
    }
  }
  const value = state.value;
  const visibleClasses = value?.classes.filter(
    (cls) =>
      (!termFilter || cls.term_id === termFilter) &&
      (!locationFilter || cls.location_id === locationFilter) &&
      (!classFilter || cls.id === classFilter),
  );
  return (
    <>
      <PageHeader
        eyebrow="CLASSES IN THEIR PLACE"
        title="The studio timetable."
      >
        Explore regular classes and dated sessions. Rosters show enrolment, not
        makeup availability.
      </PageHeader>
      <ErrorBox error={state.error} retry={state.refresh} />
      {state.loading ? (
        <Loading />
      ) : (
        value && (
          <>
            <div className="panel filters timetable-filters">
              <div className="timetable-filter-title">
                <strong>Find a class</strong>
                <span>Filter by term or location</span>
              </div>
              <label className="select-field">
                <span>Term</span>
                <div className="timetable-select-wrap">
                  <select
                    aria-label="Filter term"
                    value={termFilter}
                    onChange={(event) => setTermFilter(event.target.value)}
                  >
                    <option value="">All terms</option>
                    {value.terms.map((term) => (
                      <option value={term.id} key={term.id}>
                        {term.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={16} aria-hidden="true" />
                </div>
              </label>
              <label className="select-field">
                <span>Location</span>
                <div className="timetable-select-wrap">
                  <select
                    aria-label="Filter location"
                    value={locationFilter}
                    onChange={(event) => setLocationFilter(event.target.value)}
                  >
                    <option value="">All locations</option>
                    {value.locations.map((location) => (
                      <option value={location.id} key={location.id}>
                        {location.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={16} aria-hidden="true" />
                </div>
              </label>
              {classFilter && (
                <button className="text-button" onClick={() => setParams({})}>
                  Clear class filter <X size={13} />
                </button>
              )}
            </div>
            <div className="timetable-section-heading">
              <h2>Classes</h2>
              <span>
                {visibleClasses?.length || 0}{" "}
                {visibleClasses?.length === 1 ? "class" : "classes"}
              </span>
            </div>
            <div className="class-grid">
              {visibleClasses?.length ? (
                visibleClasses.map((cls) => {
                  const location = value.locations.find(
                      (row) => row.id === cls.location_id,
                    ),
                    term = value.terms.find((row) => row.id === cls.term_id);
                  const nameParts = cls.name
                    .split(" · ")
                    .map((part) => part.trim());
                  const weekday = nameParts.find((part) =>
                    /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$/i.test(
                      part,
                    ),
                  );
                  const titleParts = nameParts.filter(
                    (part) =>
                      part.toLowerCase() !== cls.level.trim().toLowerCase() &&
                      part !== weekday,
                  );
                  const classTitle = titleParts.join(" · ") || cls.name;
                  const locationParts = location?.name.split(" · ") || [];
                  const locationPrefix = locationParts.slice(0, -1).join(" · ");
                  const locationSuffix = locationParts.at(-1);
                  const canShortenLocation =
                    locationParts.length > 1 &&
                    value.locations.length > 1 &&
                    value.locations.every((item) => {
                      const parts = item.name.split(" · ");
                      return (
                        parts.length > 1 &&
                        parts.slice(0, -1).join(" · ") === locationPrefix
                      );
                    }) &&
                    value.locations.filter(
                      (item) =>
                        item.name.split(" · ").at(-1) === locationSuffix,
                    ).length === 1;
                  const locationLabel = canShortenLocation
                    ? locationSuffix
                    : location?.name;
                  return (
                    <section className="panel class-card" key={cls.id}>
                      <div className="class-card-header">
                        <h2>{classTitle}</h2>
                        <div className="class-tags">
                          {cls.level && (
                            <span className="class-tag-level">{cls.level}</span>
                          )}
                          {weekday && (
                            <span
                              className="class-tag-day"
                              aria-label={weekday}
                            >
                              {weekday.slice(0, 3)}
                            </span>
                          )}
                          {locationLabel && (
                            <span className="class-tag-location">
                              {locationLabel}
                            </span>
                          )}
                        </div>
                        <p className="class-meta">{term?.name}</p>
                        {location?.address && (
                          <p className="class-address">{location.address}</p>
                        )}
                        {cls.prerequisites && (
                          <p className="prerequisites">
                            <strong>Prerequisites</strong> {cls.prerequisites}
                          </p>
                        )}
                      </div>
                      <div className="session-list">
                        <div className="session-list-heading">
                          Sessions{" "}
                          <span>Select a session to view students</span>
                        </div>
                        {value.sessions
                          .filter((row) => row.class_id === cls.id)
                          .map((session) => (
                            <div className="session-entry" key={session.id}>
                              <button
                                className={`session-row ${session.id === selectedSession ? "selected" : ""}`}
                                onClick={() =>
                                  setParams(
                                    session.id === selectedSession
                                      ? {}
                                      : { session: session.id },
                                  )
                                }
                                aria-expanded={session.id === selectedSession}
                              >
                                <CalendarDays size={17} />
                                <span>
                                  {timeLabel(
                                    session.starts_at,
                                    location?.timezone,
                                  )}
                                  <small>
                                    {location?.timezone} · Capacity{" "}
                                    {session.capacity}
                                  </small>
                                </span>
                                <span className="session-action">
                                  {session.id === selectedSession
                                    ? "Close"
                                    : "Students"}{" "}
                                  <ArrowUpRight size={15} />
                                </span>
                              </button>
                              {session.id === selectedSession && (
                                <div className="session-roster">
                                  <h3>Students</h3>
                                  {workspace && (
                                    <p className="muted">
                                      Record attendance after the session ends.
                                    </p>
                                  )}
                                  {attendanceError && (
                                    <p role="alert">{attendanceError}</p>
                                  )}
                                  {value.roster.length ? (
                                    value.roster.map((student) => (
                                      <div key={student.id}>
                                        <Link
                                          className="session-student"
                                          to={`${base}/students/${student.id}`}
                                        >
                                          <span className="avatar">
                                            {student.display_name[0]}
                                          </span>
                                          <strong>
                                            {student.display_name}
                                          </strong>
                                          <ArrowUpRight size={14} />
                                        </Link>
                                        {workspace && (
                                          <label>
                                            Attendance for{" "}
                                            {student.display_name}{" "}
                                            <select
                                              value={
                                                value.attendance[student.id] ||
                                                "unknown"
                                              }
                                              disabled={
                                                attendanceBusy ||
                                                new Date(
                                                  session.ends_at,
                                                ).getTime() > Date.now()
                                              }
                                              onChange={(event) =>
                                                void saveAttendance(
                                                  student.id,
                                                  event.target.value,
                                                )
                                              }
                                            >
                                              <option value="unknown">
                                                Unknown
                                              </option>
                                              <option value="attended">
                                                Attended
                                              </option>
                                              <option value="absent">
                                                Absent
                                              </option>
                                            </select>
                                          </label>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <p className="muted">
                                      No students assigned to this session.
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                      </div>
                    </section>
                  );
                })
              ) : (
                <Empty>No classes match these filters.</Empty>
              )}
            </div>
            <div className="panel term-location-grid timetable-reference">
              <div>
                <h2>Teaching periods</h2>
                {value.terms.map((term) => (
                  <p key={term.id}>
                    <strong>{term.name}</strong>
                    <br />
                    <span className="muted">
                      {dateLabel(term.starts_on)} – {dateLabel(term.ends_on)}
                    </span>
                  </p>
                ))}
              </div>
              <div>
                <h2>Locations</h2>
                {value.locations.map((loc) => (
                  <p key={loc.id}>
                    <strong>{loc.name}</strong>
                    <br />
                    <span className="muted">
                      {loc.address}
                      <br />
                      {loc.timezone}
                    </span>
                  </p>
                ))}
              </div>
            </div>
          </>
        )
      )}
    </>
  );
}

function DatabaseBrowser() {
  const { workspace } = useSite();
  const [params, setParams] = useSearchParams();
  const catalog = useLoad(
    () => get<DatabaseTable[]>(workspace, "/database"),
    [workspace],
  );
  const requested = params.get("table") || "students";
  const selected = catalog.value?.find((table) => table.name === requested);
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const [limit, setLimit] = useState(20);
  function selectTable(name: string) {
    setParams({ table: name });
  }
  function selectOffset(next: number) {
    setParams({ table: requested, offset: String(next) });
  }
  return (
    <>
      <PageHeader
        eyebrow="THE DATA BEHIND THE DRAFT"
        title="Database"
        action={
          <button className="button secondary" onClick={catalog.refresh}>
            <RefreshCw size={16} /> Refresh database
          </button>
        }
      >
        Browse every application table and its stored records.
        {workspace
          ? " Showing live workspace data."
          : " Showing curated fictional example data."}
      </PageHeader>
      <ErrorBox error={catalog.error} retry={catalog.refresh} />
      {catalog.loading ? (
        <Loading />
      ) : (
        catalog.value && (
          <div className="database-layout">
            <nav className="panel database-tables" aria-label="Database tables">
              <div className="section-heading">
                <h2>Tables</h2>
                <span className="muted">{catalog.value.length}</span>
              </div>
              {catalog.value.map((table) => (
                <button
                  key={table.name}
                  className={`database-table-choice ${table.name === requested ? "selected" : ""}`}
                  aria-pressed={table.name === requested}
                  onClick={() => selectTable(table.name)}
                >
                  <span>
                    <Database size={15} />
                    <code>{table.name}</code>
                  </span>
                  <span className="database-count">{table.total}</span>
                </button>
              ))}
            </nav>
            {selected ? (
              <DatabaseRows
                key={`${workspace}-${selected.name}`}
                table={selected}
                offset={offset}
                limit={limit}
                onOffset={selectOffset}
                onLimit={(next) => {
                  setLimit(next);
                  selectOffset(0);
                }}
              />
            ) : (
              <div className="panel">
                <Empty>Choose a table to browse its records.</Empty>
              </div>
            )}
          </div>
        )
      )}
    </>
  );
}

function DatabaseRows({
  table,
  offset,
  limit,
  onOffset,
  onLimit,
}: {
  table: DatabaseTable;
  offset: number;
  limit: number;
  onOffset: (offset: number) => void;
  onLimit: (limit: number) => void;
}) {
  const { workspace } = useSite();
  const { value, error, loading, refresh } = useLoad(async () => {
    const [records, students] = await Promise.all([
      get<Page<DatabaseRecord>>(workspace, `/database/${table.name}`, {
        limit,
        offset,
      }),
      table.name === "class_sessions"
        ? all<Student>(workspace, "/students")
        : Promise.resolve([] as Student[]),
    ]);
    return {
      ...records,
      studentNames: Object.fromEntries(
        students.map((student) => [student.id, student.display_name]),
      ),
    };
  }, [workspace, table.name, limit, offset]);
  return (
    <section
      className="panel database-records"
      aria-label={`${table.name} records`}
    >
      <div className="section-heading">
        <div>
          <h2>{table.name}</h2>
          <p className="muted">
            {value?.total ?? table.total} records · {table.columns.length}{" "}
            columns
          </p>
        </div>
        <button
          className="icon-button"
          aria-label="Refresh table"
          onClick={refresh}
        >
          <RefreshCw size={18} />
        </button>
      </div>
      <div className="database-controls">
        <p className="muted">
          Scroll across to see all columns. Expand JSON values to inspect their
          contents.
        </p>
        <label>
          Rows per page
          <select
            value={limit}
            onChange={(event) => onLimit(Number(event.target.value))}
          >
            {[20, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ErrorBox error={error} retry={refresh} />
      {loading ? (
        <Loading />
      ) : (
        !error &&
        value && (
          <>
            <div
              className="database-scroll"
              tabIndex={0}
              role="region"
              aria-label={`${table.name} data`}
            >
              <table className="database-grid">
                <caption className="sr-only">
                  All stored columns in {table.name}
                </caption>
                <thead>
                  <tr>
                    {table.columns.map((column) => (
                      <th key={column} scope="col">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {value.items.map((row) => (
                    <tr key={String(row.id)}>
                      {table.columns.map((column) => (
                        <td key={column}>
                          {table.name === "class_sessions" &&
                          column === "students" &&
                          Array.isArray(row[column]) ? (
                            <div className="database-value">
                              {(row[column] as string[]).length ? (
                                (row[column] as string[]).map((id) => (
                                  <div key={id}>
                                    <Link
                                      to={`${workspace ? "/workspace" : "/demo"}/students/${id}`}
                                    >
                                      {value.studentNames[id] || id}
                                    </Link>
                                  </div>
                                ))
                              ) : (
                                <span className="muted">No students</span>
                              )}
                            </div>
                          ) : (
                            <DatabaseCell value={row[column]} />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!value.items.length && (
              <Empty>
                {value.total
                  ? "No records on this page. Use Previous page to go back."
                  : "This table has no records yet."}
              </Empty>
            )}
            <Pager page={value} onChange={onOffset} />
          </>
        )
      )}
    </section>
  );
}

function DatabaseCell({ value }: { value: unknown }) {
  if (value === null || value === undefined)
    return <span className="muted database-null">NULL</span>;
  if (typeof value === "object")
    return (
      <details className="database-json">
        <summary>
          {Array.isArray(value)
            ? `Array (${value.length})`
            : `JSON (${Object.keys(value).length} keys)`}
        </summary>
        <Json value={value} />
      </details>
    );
  return <span className="database-value">{String(value)}</span>;
}

function TestEmail() {
  const { workspace, base, identity } = useSite();
  const navigate = useNavigate();
  const [sender, setSender] = useState(""),
    [body, setBody] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<Error>();
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(undefined);
    try {
      const run = await post<Run>(
        "/api/v1/incoming-emails",
        identity.csrf_token || "",
        { from: sender, body },
      );
      navigate(`${base}/reviews/${run.id}`);
    } catch (err) {
      setError(err as Error);
    } finally {
      setBusy(false);
    }
  }
  if (!workspace) return <CustomEmail />;
  return (
    <>
      <PageHeader
        eyebrow="THE EMAIL ENTRANCE"
        title={
          workspace
            ? "Start with an email."
            : "See how an email becomes a draft."
        }
      >
        {workspace
          ? "Submit a fictional message to the running agent and inspect its response."
          : "A small input connects to a rich conversation. Explore this predefined example."}
      </PageHeader>
      <div className="email-grid">
        <section className="panel email-form">
          <div className="section-heading compact">
            <h2>
              {workspace
                ? "Simulate an incoming email"
                : "Example incoming email"}
            </h2>
            <Mail size={20} />
          </div>
          {workspace ? (
            <form onSubmit={submit}>
              <label>
                Sender email
                <input
                  type="email"
                  required
                  maxLength={320}
                  value={sender}
                  onChange={(event) => setSender(event.target.value)}
                  placeholder="new.enquirer@example.test"
                  disabled={busy}
                />
              </label>
              <label>
                Email body
                <textarea
                  required
                  maxLength={100000}
                  rows={10}
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  placeholder="Write a fictional enquiry…"
                  disabled={busy}
                />
              </label>
              <div className="notice">
                This saves an email, updates conversational memory, and runs the
                configured paid model. An unknown sender receives a placeholder
                student profile. Use fictional content.
              </div>
              <ErrorBox error={error} />
              {error && (
                <Link
                  className="inline-link"
                  to={`${base}/reviews${sender ? `?q=${encodeURIComponent(sender)}` : ""}`}
                >
                  Check the queue before submitting again{" "}
                  <ArrowRight size={15} />
                </Link>
              )}
              <button
                className="button primary"
                disabled={busy || !sender || !body.trim()}
              >
                {busy ? (
                  <>
                    <span className="spinner" />
                    Generating a draft…
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    Submit email and generate draft
                  </>
                )}
              </button>
            </form>
          ) : null}
        </section>
        <aside className="panel email-explainer">
          <div className="eyebrow">WHAT HAPPENS NEXT</div>
          {[
            [
              "Find the conversation",
              "Match the sender and load their message history.",
            ],
            [
              "Read the latest request",
              "Understand corrections in the context of earlier emails.",
            ],
            [
              "Connect the evidence",
              "Inspect student memory and the regular class timetable.",
            ],
            [
              "Prepare a reviewable response",
              "Give the teacher a draft, rationale, and unanswered questions.",
            ],
          ].map(([title, text], index) => (
            <div className="email-step" key={title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </div>
          ))}
          <div className="notice">
            Receiving a real inbox email is a future integration. This entrance
            currently accepts a recorded or simulated message.
          </div>
        </aside>
      </div>
    </>
  );
}
