import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../lib/types";

interface RoleRouteProps {
  roles: Role[];
  children: ReactNode;
}

/**
 * The default landing page for a role. Used whenever an authenticated user
 * hits a route they are not permitted to access; instead of a fixed redirect
 * to /dashboard (which would loop forever for a PLATFORM_ADMIN, who is not
 * allowed on /dashboard), we route them to their own role home.
 */
export function roleHomePath(role: Role): string {
  return role === "PLATFORM_ADMIN" ? "/admin" : "/dashboard";
}

/**
 * Role-aware guard. Renders `children` only when the authenticated user's
 * role is within `roles`; otherwise redirects to the role's own home page.
 * This is UI-only gating — the backend enforces authorization.
 */
export function RoleRoute({ roles, children }: RoleRouteProps) {
  const { user } = useAuth();

  if (!user || !roles.includes(user.role)) {
    return <Navigate to={roleHomePath(user?.role ?? "MERCHANT")} replace />;
  }

  return <>{children}</>;
}
