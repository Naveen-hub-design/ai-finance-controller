import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api } from "../lib/api";
import { useAuth } from "./AuthContext";
import type { BusinessesResponse, BusinessWithRole } from "../lib/types";

export interface BusinessContextValue {
  /** Businesses the authenticated user is a member of. */
  businesses: BusinessWithRole[];
  /** Id of the currently selected business, or null for Personal scope. */
  selectedBusinessId: string | null;
  /** The currently selected business object, or null for Personal scope. */
  selectedBusiness: BusinessWithRole | null;
  /** True on first load while businesses are being fetched. */
  isLoading: boolean;
  /** Select a business by id (null clears to Personal scope). */
  selectBusiness: (id: string | null) => void;
  /** Re-fetch the user's businesses. */
  refresh: () => Promise<void>;
  /**
   * Build a query-string suffix (`?business_id=...`) for financial API calls.
   * Pass the current selection by default, or an explicit id to override.
   */
  businessQuery: (businessId?: string | null) => string;
  /** True when the user has a business scope selected (not Personal). */
  isBusinessScope: boolean;
}

const BusinessContext = createContext<BusinessContextValue | null>(null);

export function BusinessProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [businesses, setBusinesses] = useState<BusinessWithRole[]>([]);
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const didAutoSelectRef = useRef(false);

  const refresh = useCallback(async () => {
    // The business selector only applies to roles that belong to businesses.
    if (!user || user.role === "PLATFORM_ADMIN") {
      setBusinesses([]);
      setSelectedBusinessId(null);
      return;
    }
    setIsLoading(true);
    try {
      const res = await api.get<BusinessesResponse>("/businesses");
      const list = res.businesses ?? [];
      setBusinesses(list);
      setSelectedBusinessId((prev) => {
        // If the currently selected business was removed, fall back to Personal.
        if (prev !== null && !list.some((b) => b.id === prev)) return null;
        // Auto-select first permitted business on initial load so Finance
        // Manager (and Merchant) dashboards show real business data instead
        // of an empty Personal scope. Respects explicit Personal choice
        // (didAutoSelectRef prevents re-selecting after user chose Personal).
        if (prev === null && list.length > 0 && !didAutoSelectRef.current) {
          const stored = (() => {
            try { return localStorage.getItem("businessSelection"); } catch { return null; }
          })();
          if (stored === "personal") {
            didAutoSelectRef.current = true;
            return null;
          }
          didAutoSelectRef.current = true;
          return list[0].id;
        }
        return prev;
      });
    } catch {
      setBusinesses([]);
      setSelectedBusinessId(null);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectBusiness = useCallback((id: string | null) => {
    didAutoSelectRef.current = true;
    try {
      if (id === null) localStorage.setItem("businessSelection", "personal");
      else localStorage.removeItem("businessSelection");
    } catch { /* ignore */ }
    setSelectedBusinessId(id);
  }, []);

  const selectedBusiness = useMemo(
    () => businesses.find((b) => b.id === selectedBusinessId) ?? null,
    [businesses, selectedBusinessId]
  );

  const businessQuery = useCallback(
    (businessId?: string | null) => {
      const id =
        businessId === undefined ? selectedBusinessId : businessId;
      return id ? `?business_id=${encodeURIComponent(id)}` : "";
    },
    [selectedBusinessId]
  );

  const value = useMemo<BusinessContextValue>(
    () => ({
      businesses,
      selectedBusinessId,
      selectedBusiness,
      isLoading,
      selectBusiness,
      refresh,
      businessQuery,
      isBusinessScope: selectedBusinessId !== null,
    }),
    [
      businesses,
      selectedBusinessId,
      selectedBusiness,
      isLoading,
      selectBusiness,
      refresh,
      businessQuery,
    ]
  );

  return (
    <BusinessContext.Provider value={value}>
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness(): BusinessContextValue {
  const ctx = useContext(BusinessContext);
  if (!ctx) {
    throw new Error("useBusiness must be used within a BusinessProvider");
  }
  return ctx;
}
