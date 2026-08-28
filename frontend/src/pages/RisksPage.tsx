import { ShieldAlert } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function RisksPage() {
  return (
    <PageScaffold
      title="Risks"
      description="Anomaly detection and risk flags surfaced from your financial activity."
      icon={ShieldAlert}
    />
  );
}
