import { useParams } from "react-router-dom";
import { Receipt } from "lucide-react";
import { PageScaffold } from "./PageScaffold";

export default function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <PageScaffold
      title="Transaction Details"
      description={`Reviewing transaction ${id ? `#${id}` : "detail"}.`}
      icon={Receipt}
    />
  );
}
