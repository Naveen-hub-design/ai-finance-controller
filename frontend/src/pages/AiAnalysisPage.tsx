import { useState } from "react";
import {
  BrainCircuit,
  HeartPulse,
  Sparkles,
  Send,
  CircleDollarSign,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

function InsightCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-accent-400" aria-hidden="true" />
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </Card>
  );
}

export default function AiAnalysisPage() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState(false);

  const handleAsk = () => {
    if (!question.trim()) return;
    setAsked(true);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Analysis"
        description="Deep-dive AI insights across your accounts, trends, and anomalies."
      />

      <section aria-labelledby="health-overview">
        <SectionHeading
          title="Financial Health Overview"
          description="Key health indicators computed from your financial data."
        />
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            label="Net Worth"
            icon={HeartPulse}
            value={<span className="text-muted">Unavailable</span>}
            hint="Total assets minus liabilities"
          />
          <StatCard
            label="Savings Rate"
            icon={TrendingUp}
            value={<span className="text-muted">Unavailable</span>}
            hint="Share of income saved"
          />
          <StatCard
            label="Spending Trend"
            icon={TrendingDown}
            value={<span className="text-muted">Unavailable</span>}
            hint="Direction of spending over time"
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
              <BrainCircuit className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-foreground">
                Ask AI about your finances
              </h3>
              <p className="text-xs text-muted">
                Get an explanation or insight from your financial data.
              </p>
            </div>
          </div>

          <div className="mt-4">
            <label htmlFor="ai-question" className="sr-only">
              Your financial question
            </label>
            <textarea
              id="ai-question"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Explain my spending this month — which categories grew?"
              className="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 focus:border-accent-500 focus:outline-none disabled:opacity-50"
            />
          </div>

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-muted-faint">
              AI responses require a configured provider and an authenticated
              session (planned for a later milestone).
            </p>
            <Button onClick={handleAsk} disabled={!question.trim()}>
              <Send className="h-4 w-4" aria-hidden="true" />
              Ask
            </Button>
          </div>

          {asked && (
            <div className="mt-4 rounded-lg border border-border bg-surface-raised/40 p-4">
              <Badge tone="warning">Service unavailable</Badge>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                The AI service is not reachable yet. This is expected in the
                current milestone: the provider is not configured and there is
                no authenticated session. Local 502/503 responses will be shown
                cleanly here once integration is wired in.
              </p>
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <SectionHeading
            title="Insights"
            description="Generated observations about your financial patterns."
          />
          <InsightCard
            title="Awaiting data"
            description="Insights will appear here once your financial data is available for analysis."
          />
          <InsightCard
            title="Awaiting data"
            description="Trends, anomalies, and opportunities will be surfaced here as the AI analysis runs."
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionHeading
            title="Financial Facts"
            description="A snapshot of your current financial position."
          />
          <div className="mt-4">
            <EmptyState
              icon={CircleDollarSign}
              title="Financial facts unavailable"
              description="Your current income, expenses, balance, and key ratios will be summarized here."
            />
          </div>
        </Card>

        <Card className="p-5">
          <SectionHeading
            title="Goal Intelligence"
            description="AI guidance toward your financial goals and the feasibility of reaching them."
          />
          <div className="mt-4">
            <EmptyState
              icon={TrendingUp}
              title="Goal intelligence unavailable"
              description="Once goals exist, the AI will assess progress and suggest adjustments to stay on track."
            />
          </div>
        </Card>
      </section>
    </div>
  );
}
