import { LayoutDashboard } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function DashboardPage() {
  return (
    <PageScaffold
      title="Dashboard"
      description="A high-level view of your financial health, upcoming obligations, and key metrics."
      icon={LayoutDashboard}
    />
  );
}
