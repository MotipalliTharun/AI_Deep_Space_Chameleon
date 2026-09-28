import { useState } from "preact/hooks";
import type { ThemeTokens } from "../theme/extractTheme";

export interface BubbleProps {
  siteId: string;
  theme: ThemeTokens;
}

/**
 * The always-visible chat bubble. Opening it lazy-loads the full chat panel
 * (RAG answers, task progress card, "talk to a human" — FR-3, FR-5) so the
 * initial loader stays under the 15 KB budget.
 */
export function Bubble({ siteId, theme }: BubbleProps) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        fontFamily: theme.fontFamily,
      }}
    >
      <button
        aria-label="Open support chat"
        onClick={() => setOpen((v) => !v)}
        style={{
          background: theme.primaryColor,
          color: "#fff",
          border: "none",
          borderRadius: "999px",
          width: "56px",
          height: "56px",
          cursor: "pointer",
        }}
      >
        💬
      </button>
      {open && (
        // TODO(sprint-1): dynamic import() the chat panel bundle here.
        <div
          role="dialog"
          aria-label="Support chat"
          style={{
            position: "absolute",
            bottom: "70px",
            right: 0,
            width: "320px",
            height: "420px",
            background: theme.backgroundColor,
            borderRadius: theme.cornerRadius,
            boxShadow: "0 4px 24px rgba(0,0,0,0.15)",
            padding: "16px",
          }}
        >
          <p>Chat panel placeholder — site {siteId}</p>
        </div>
      )}
    </div>
  );
}
