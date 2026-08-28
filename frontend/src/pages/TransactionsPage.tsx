import { ArrowLeftRight } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function TransactionsPage() {
  return (
    <PageScaffold
      title="Transactions"
      description="Search, filter, and review your income and expenses in one place."
      icon={ArrowLeftRight}
    />
  );
}
