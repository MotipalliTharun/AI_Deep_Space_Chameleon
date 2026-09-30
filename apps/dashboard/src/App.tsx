import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RedirectIfAuthenticated, RequireAuth, RequireRole } from "./auth/guards";
import { ADMIN_ROLES } from "./lib/types";
import type { Role } from "./lib/types";
import { Account } from "./pages/Account";
import { AgentInbox } from "./pages/AgentInbox";
import { AuditLog } from "./pages/AuditLog";
import { Conversations } from "./pages/Conversations";
import { FeedbackInbox } from "./pages/FeedbackInbox";
import { Knowledge } from "./pages/Knowledge";
import { Login } from "./pages/Login";
import { Setup } from "./pages/Setup";
import { Signup } from "./pages/Signup";
import { Tasks } from "./pages/Tasks";
import { Team } from "./pages/Team";

// Admin dashboard sections per PRD §5 scope: setup, knowledge, tasks,
// conversations/analytics, feedback inbox — plus the agent inbox (§8).
const NAV: { to: string; label: string; roles?: readonly Role[] }[] = [
  { to: "/inbox", label: "Agent inbox" },
  { to: "/conversations", label: "Conversations" },
  { to: "/tasks", label: "Tasks" },
  { to: "/feedback", label: "Feedback inbox" },
  { to: "/knowledge", label: "Knowledge", roles: ADMIN_ROLES },
  { to: "/setup", label: "Setup", roles: ADMIN_ROLES },
  { to: "/team", label: "Team", roles: ADMIN_ROLES },
  { to: "/audit", label: "Audit log", roles: ADMIN_ROLES },
];

function Shell() {
  const { user, tenant, logout, hasRole } = useAuth();
  return (
    <div className="flex h-screen">
      <nav aria-label="Main" className="flex w-56 flex-col border-r bg-white p-4">
        <p className="mb-4 truncate px-2 text-sm font-semibold" title={tenant?.name}>
          {tenant?.name}
        </p>
        <div className="space-y-1">
          {NAV.filter((item) => !item.roles || hasRole(...item.roles)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded px-2 py-1 text-sm ${isActive ? "bg-emerald-50 font-medium text-emerald-800" : "text-gray-700 hover:bg-gray-100"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
        <div className="mt-auto border-t pt-3 text-sm">
          <NavLink to="/account" className="block truncate rounded px-2 py-1 hover:bg-gray-100">
            <span className="block truncate font-medium">{user?.full_name || user?.email}</span>
            <span className="block text-xs capitalize text-gray-500">{user?.role}</span>
          </NavLink>
          <button
            type="button"
            onClick={() => void logout()}
            className="mt-1 w-full rounded px-2 py-1 text-left text-gray-600 hover:bg-gray-100"
          >
            Sign out
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-auto bg-gray-50 p-6">
        <Outlet />
      </main>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<RedirectIfAuthenticated />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route index element={<Navigate to="/inbox" replace />} />
          <Route path="/inbox" element={<AgentInbox />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/feedback" element={<FeedbackInbox />} />
          <Route path="/account" element={<Account />} />
          <Route element={<RequireRole roles={ADMIN_ROLES} />}>
            <Route path="/setup" element={<Setup />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/team" element={<Team />} />
            <Route path="/audit" element={<AuditLog />} />
          </Route>
          <Route path="*" element={<Navigate to="/inbox" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
