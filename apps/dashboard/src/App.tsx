import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { Setup } from "./pages/Setup";
import { Knowledge } from "./pages/Knowledge";
import { Tasks } from "./pages/Tasks";
import { Conversations } from "./pages/Conversations";
import { FeedbackInbox } from "./pages/FeedbackInbox";
import { AgentInbox } from "./pages/AgentInbox";

// Admin dashboard sections per PRD §5 scope: setup, knowledge, tasks,
// conversations/analytics, feedback inbox — plus the agent inbox (§8).
const NAV = [
  { to: "/setup", label: "Setup" },
  { to: "/knowledge", label: "Knowledge" },
  { to: "/tasks", label: "Tasks" },
  { to: "/conversations", label: "Conversations" },
  { to: "/feedback", label: "Feedback inbox" },
  { to: "/inbox", label: "Agent inbox" },
];

export function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen">
        <nav className="w-56 border-r p-4 space-y-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className="block rounded px-2 py-1 hover:bg-gray-100"
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/setup" element={<Setup />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/feedback" element={<FeedbackInbox />} />
            <Route path="/inbox" element={<AgentInbox />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
