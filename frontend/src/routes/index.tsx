import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import DashboardPage from "../pages/DashboardPage";
import AccountsPage from "../pages/AccountsPage";
import TransactionsPage from "../pages/TransactionsPage";
import TransactionDetailPage from "../pages/TransactionDetailPage";
import CategoriesPage from "../pages/CategoriesPage";
import BudgetsPage from "../pages/BudgetsPage";
import GoalsPage from "../pages/GoalsPage";
import AiControllerPage from "../pages/AiControllerPage";
import AiAnalysisPage from "../pages/AiAnalysisPage";
import RisksPage from "../pages/RisksPage";
import RecommendationsPage from "../pages/RecommendationsPage";
import AuditPage from "../pages/AuditPage";
import SettingsPage from "../pages/SettingsPage";
import LoginPage from "../pages/LoginPage";
import NotFoundPage from "../pages/NotFoundPage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route
            path="/transactions/:id"
            element={<TransactionDetailPage />}
          />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/budgets" element={<BudgetsPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/ai-controller" element={<AiControllerPage />} />
          <Route path="/ai-analysis" element={<AiAnalysisPage />} />
          <Route path="/risks" element={<RisksPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
