import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { ProtectedRoute } from "./ProtectedRoute";
import { RoleRoute, roleHomePath } from "./RoleRoute";
import { PublicOnlyRoute } from "./PublicOnlyRoute";
import { useAuth } from "../context/AuthContext";
import DashboardPage from "../pages/DashboardPage";
import FinanceDashboardPage from "../pages/FinanceDashboardPage";
import AdminDashboardPage from "../pages/AdminDashboardPage";
import UserManagementPage from "../pages/UserManagementPage";
import AccountsPage from "../pages/AccountsPage";
import TransactionsPage from "../pages/TransactionsPage";
import TransactionDetailPage from "../pages/TransactionDetailPage";
import CategoriesPage from "../pages/CategoriesPage";
import BudgetsPage from "../pages/BudgetsPage";
import GoalsPage from "../pages/GoalsPage";
import BusinessesPage from "../pages/BusinessesPage";
import AiControllerPage from "../pages/AiControllerPage";
import AiAnalysisPage from "../pages/AiAnalysisPage";
import RisksPage from "../pages/RisksPage";
import RecommendationsPage from "../pages/RecommendationsPage";
import ReconciliationPage from "../pages/ReconciliationPage";
import AuditPage from "../pages/AuditPage";
import SettingsPage from "../pages/SettingsPage";
import LoginPage from "../pages/LoginPage";
import NotFoundPage from "../pages/NotFoundPage";

function RoleAwareHome() {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Navigate to={roleHomePath(user.role)} replace />;
}

/** Renders the correct dashboard for the authenticated non-admin role. */
function FinancialDashboard() {
  const { user } = useAuth();
  if (user?.role === "FINANCE_MANAGER") {
    return <FinanceDashboardPage />;
  }
  return <DashboardPage />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route
              path="/"
              element={<RoleAwareHome />}
            />
            <Route
              path="/admin"
              element={
                <RoleRoute roles={["PLATFORM_ADMIN"]}>
                  <AdminDashboardPage />
                </RoleRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <RoleRoute roles={["PLATFORM_ADMIN"]}>
                  <UserManagementPage />
                </RoleRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}>
                  <FinancialDashboard />
                </RoleRoute>
              }
            />
            <Route path="/accounts" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><AccountsPage /></RoleRoute>} />
            <Route path="/transactions" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><TransactionsPage /></RoleRoute>} />
            <Route
              path="/transactions/:id"
              element={
                <RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}>
                  <TransactionDetailPage />
                </RoleRoute>
              }
            />
            <Route path="/categories" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><CategoriesPage /></RoleRoute>} />
            <Route path="/budgets" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><BudgetsPage /></RoleRoute>} />
            <Route path="/goals" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><GoalsPage /></RoleRoute>} />
            <Route
              path="/businesses"
              element={
                <RoleRoute roles={["MERCHANT"]}>
                  <BusinessesPage />
                </RoleRoute>
              }
            />
            <Route path="/ai-controller" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><AiControllerPage /></RoleRoute>} />
            <Route path="/ai-analysis" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><AiAnalysisPage /></RoleRoute>} />
            <Route path="/risks" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><RisksPage /></RoleRoute>} />
            <Route path="/recommendations" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><RecommendationsPage /></RoleRoute>} />
            <Route path="/reconcile" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><ReconciliationPage /></RoleRoute>} />
            <Route path="/audit" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER"]}><AuditPage /></RoleRoute>} />
            <Route path="/settings" element={<RoleRoute roles={["MERCHANT", "FINANCE_MANAGER", "PLATFORM_ADMIN"]}><SettingsPage /></RoleRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
