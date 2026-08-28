import { Sparkles } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function AiControllerPage() {
  return (
    <PageScaffold
      title="AI Controller"
      description="Send a natural-language instruction and receive an AI-generated financial report and recommendations."
      icon={Sparkles}
    />
  );
}
