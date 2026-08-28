import { Target } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function GoalsPage() {
  return (
    <PageScaffold
      title="Goals"
      description="Track progress toward your savings and financial goals."
      icon={Target}
    />
  );
}
