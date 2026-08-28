import { BrainCircuit } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function AiAnalysisPage() {
  return (
    <PageScaffold
      title="AI Analysis"
      description="Deep-dive AI insights across your accounts, trends, and anomalies."
      icon={BrainCircuit}
    />
  );
}
