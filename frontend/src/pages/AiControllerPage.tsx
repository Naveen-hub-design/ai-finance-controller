import { useEffect, useRef, useState } from "react";
import {
  Send,
  RotateCcw,
  Loader2,
  CheckCircle2,
  CircleX,
  BrainCircuit,
  ShieldAlert,
  ThumbsUp,
  Workflow,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

type Phase = "idle" | "submitting" | "running" | "succeeded" | "failed";

const REPORT_SECTIONS = [
  { key: "overview", label: "Summary & overview" },
  { key: "risks", label: "Risk assessment" },
  { key: "recommendations", label: "Recommendations" },
];

export default function AiControllerPage() {
  const [instruction, setInstruction] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [selectedSection, setSelectedSection] = useState("overview");
  const timers = useRef<number[]>([]);

  const clearTimers = () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  };

  useEffect(() => clearTimers, []);

  const startFlow = () => {
    if (!instruction.trim()) return;
    clearTimers();
    setPhase("submitting");
    timers.current.push(
      window.setTimeout(() => {
        setPhase("running");
        timers.current.push(
          window.setTimeout(() => {
            setPhase("succeeded");
          }, 2600)
        );
      }, 700)
    );
  };

  const reset = () => {
    clearTimers();
    setPhase("idle");
    setInstruction("");
  };

  const busy = phase === "submitting" || phase === "running";

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Controller"
        description="Send a natural-language instruction and receive an AI-generated financial report and recommendations."
      />

      <Card className="p-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
            <BrainCircuit className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold tracking-tight text-foreground">
              Run the controller
            </h2>
            <p className="text-sm text-muted">
              Describe what you want the controller to do with your finances.
            </p>
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor="instruction" className="sr-only">
            Controller instruction
          </label>
          <textarea
            id="instruction"
            rows={3}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            disabled={busy}
            placeholder="e.g. Review my spending this month and flag anything unusual."
            className="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 focus:border-accent-500 focus:outline-none disabled:opacity-50"
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-faint">
            Submission is API-ready but not yet connected. Wiring to
            POST&nbsp;/api/users/&#123;id&#125;/ai-controller/async and polling
            the task status endpoint is deferred until authentication exists.
          </p>
          <div className="flex items-center gap-2">
            {busy && (
              <Button variant="ghost" size="sm" onClick={reset}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset
              </Button>
            )}
            <Button onClick={startFlow} disabled={!instruction.trim() || busy}>
              {phase === "submitting" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
              {phase === "succeeded" || phase === "failed"
                ? "Run again"
                : "Submit"}
            </Button>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2.5">
          <Workflow className="h-5 w-5 text-accent-400" aria-hidden="true" />
          <h2 className="text-base font-semibold tracking-tight text-foreground">
            Task status
          </h2>
        </div>

        {phase === "idle" && (
          <p className="mt-4 rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-4 text-sm text-muted">
            Submit an instruction to start an asynchronous controller run. The
            current milestone demonstrates the run lifecycle; real task
            dispatch and status polling are wired in a later milestone.
          </p>
        )}

        {phase === "submitting" && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface-raised/40 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">Submitting task</p>
              <p className="text-xs text-muted">Sending your instruction…</p>
            </div>
          </div>
        )}

        {phase === "running" && (
          <div className="mt-4 rounded-lg border border-border bg-surface-raised/40 p-4">
            <div className="flex items-center gap-2">
              <Badge tone="accent">RUNNING</Badge>
              <span className="text-xs text-muted">Task submitted and running</span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-accent-400" aria-hidden="true" />
              <p className="text-sm text-muted">
                Polling for status — the controller is preparing your report.
              </p>
            </div>
          </div>
        )}

        {phase === "succeeded" && (
          <div className="mt-4">
            <div className="rounded-lg border border-success-500/25 bg-success-500/5 p-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-success-500" aria-hidden="true" />
                <Badge tone="success">SUCCESS</Badge>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                The controller run reported a completed result. Because data
                integration is not yet connected, the report sections below are
                placeholders awaiting real data — no financial figures are
                shown.
              </p>
            </div>

            <div className="mt-4">
              <div className="flex flex-wrap gap-2">
                {REPORT_SECTIONS.map((s) => (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => setSelectedSection(s.key)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      selectedSection === s.key
                        ? "bg-accent-600 text-white"
                        : "bg-surface-raised text-muted hover:text-foreground"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              <div className="mt-3 rounded-lg border border-border bg-surface-raised/30 p-4">
                {REPORT_SECTIONS.find((s) => s.key === selectedSection)
                  ?.label ?? "Report"}
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  The {selectedSection} content produced by the controller will
                  render here once the API integration and authentication are
                  in place.
                </p>
                {selectedSection === "risks" && (
                  <div className="mt-3 flex items-center gap-2 text-danger-400">
                    <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                    <span className="text-xs">No risk signals displayed (no data).</span>
                  </div>
                )}
                {selectedSection === "recommendations" && (
                  <div className="mt-3 flex items-center gap-2 text-success-500">
                    <ThumbsUp className="h-4 w-4" aria-hidden="true" />
                    <span className="text-xs">No recommendations displayed (no data).</span>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={startFlow}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
              <Button variant="ghost" size="sm" onClick={reset}>
                New instruction
              </Button>
            </div>
          </div>
        )}

        {phase === "failed" && (
          <div className="mt-4 rounded-lg border border-danger-500/25 bg-danger-500/5 p-4">
            <div className="flex items-center gap-2">
              <CircleX className="h-5 w-5 text-danger-400" aria-hidden="true" />
              <Badge tone="danger">FAILURE</Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              The task did not complete successfully. Error details surface
              here when task status polling is connected.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={startFlow}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
              <Button variant="ghost" size="sm" onClick={reset}>
                New instruction
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
