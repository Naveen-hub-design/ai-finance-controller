import { Tags } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function CategoriesPage() {
  return (
    <PageScaffold
      title="Categories"
      description="Organize your spending and income into categories for clearer analysis."
      icon={Tags}
    />
  );
}
