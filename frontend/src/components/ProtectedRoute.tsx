import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Loading } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";

/**
 * Gate for signed-in routes.
 *
 * Waits for the session restore to settle before deciding -- redirecting during
 * the initial check would bounce a signed-in user to the login page on every
 * hard refresh. The attempted path is passed along so sign-in can return there.
 */
export function ProtectedRoute({ staffOnly = false }: { staffOnly?: boolean }) {
  const { isAuthenticated, isStaff, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading label="Checking your session" />;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (staffOnly && !isStaff) return <Navigate to="/dashboard" replace />;

  return <Outlet />;
}
