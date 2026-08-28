import { ScrollText } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function AuditPage() {
  return (
    <PageScaffold
      title="Audit"
      description="A chronological record of AI-generated decisions, risks, and recommendations."
      icon={ScrollText}
    />
  );
}
