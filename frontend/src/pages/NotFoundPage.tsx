import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { roleHomePath } from "../routes/RoleRoute";
import { Button } from "../components/ui/Button";

export default function NotFoundPage() {
  const { user } = useAuth();
  const home = roleHomePath(user?.role ?? "MERCHANT");
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-raised text-accent-400">
        <Compass className="h-6 w-6" aria-hidden="true" />
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-foreground">
        404
      </h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        The page you're looking for doesn't exist or hasn't been built yet.
      </p>
      <div className="mt-6">
        <Link to={home}>
          <Button>Back to {home === "/admin" ? "admin" : "dashboard"}</Button>
        </Link>
      </div>
    </div>
  );
}
