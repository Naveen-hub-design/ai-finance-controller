import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { roleHomePath } from "./RoleRoute";

export function PublicOnlyRoute() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to={roleHomePath(user?.role ?? "MERCHANT")} replace />;
  }

  return <Outlet />;
}
