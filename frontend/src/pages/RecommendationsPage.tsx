import { ThumbsUp } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function RecommendationsPage() {
  return (
    <PageScaffold
      title="Recommendations"
      description="Actionable suggestions generated to improve your financial position."
      icon={ThumbsUp}
    />
  );
}
