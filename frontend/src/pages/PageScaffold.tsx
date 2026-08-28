import type { LucideIcon } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Placeholder } from "../components/ui/Placeholder";

interface PageScaffoldProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
}

export function PageScaffold({
  title,
  description,
  icon,
}: PageScaffoldProps) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} />
      <Placeholder title={title} description={description} icon={icon} />
    </div>
  );
}
