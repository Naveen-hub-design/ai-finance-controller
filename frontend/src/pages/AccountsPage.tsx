import { Wallet } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function AccountsPage() {
  return (
    <PageScaffold
      title="Accounts"
      description="All your linked accounts and their running balances at a glance."
      icon={Wallet}
    />
  );
}
