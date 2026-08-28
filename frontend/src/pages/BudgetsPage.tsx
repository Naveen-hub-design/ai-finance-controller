import { PiggyBank } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function BudgetsPage() {
  return (
    <PageScaffold
      title="Budgets"
      description="Set and monitor monthly budgets across your spending categories."
      icon={PiggyBank}
    />
  );
}
