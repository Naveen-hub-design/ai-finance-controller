import { Settings } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function SettingsPage() {
  return (
    <PageScaffold
      title="Settings"
      description="Application and account preferences."
      icon={Settings}
    />
  );
}
