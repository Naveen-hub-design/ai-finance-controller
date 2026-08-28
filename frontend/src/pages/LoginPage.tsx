import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Input } from "../components/ui/Input";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-600 text-white">
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </div>
          <span className="text-lg font-semibold tracking-tight text-foreground">
            AI Finance Controller
          </span>
        </div>

        <Card className="p-6">
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
          </CardHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => event.preventDefault()}
          >
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Email
              </label>
              <Input id="email" type="email" placeholder="you@example.com" />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
              />
            </div>

            <Button type="submit" className="w-full">
              Continue
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </form>

          <p className="mt-4 text-xs text-muted-faint">
            Authentication is planned for a later milestone. For now you can
            explore the{" "}
            <Link
              to="/dashboard"
              className="text-accent-400 underline-offset-2 hover:underline"
            >
              dashboard
            </Link>
            .
          </p>
        </Card>
      </div>
    </div>
  );
}
