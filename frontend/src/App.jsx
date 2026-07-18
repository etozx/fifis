import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import { Loading } from "./components/StateViews.jsx";

// Code-split pages so the initial bundle stays small; the chart-heavy Dashboard
// (Recharts) is only fetched when the user actually opens it.
const Login = lazy(() => import("./pages/Login.jsx"));
const Register = lazy(() => import("./pages/Register.jsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const Goals = lazy(() => import("./pages/Goals.jsx"));
const GoalDetail = lazy(() => import("./pages/GoalDetail.jsx"));
const Focus = lazy(() => import("./pages/Focus.jsx"));

/** Gate that redirects unauthenticated users to the login page. */
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center text-ink-muted">
        Loading…
      </div>
    );
  }
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/goals/:goalId" element={<GoalDetail />} />
          <Route path="/focus" element={<Focus />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
