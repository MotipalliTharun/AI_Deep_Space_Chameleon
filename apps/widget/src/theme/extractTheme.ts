export interface ThemeTokens {
  primaryColor: string;
  backgroundColor: string;
  fontFamily: string;
  cornerRadius: string;
}

/**
 * Reads the host page's computed styles and derives design tokens for the widget.
 * Owner can lock/override the result in the dashboard (FR: auto-theming, SC-40).
 * TODO(sprint-1): pick primaryColor from a real heuristic (dominant brand color,
 * not just body color); run an AA contrast check with fallback per PRD §5.
 */
export function extractTheme(root: HTMLElement): ThemeTokens {
  const computed = getComputedStyle(root);
  return {
    primaryColor: computed.getPropertyValue("--sc-primary") || "#1a73e8",
    backgroundColor: computed.backgroundColor || "#ffffff",
    fontFamily: computed.fontFamily || "system-ui, sans-serif",
    cornerRadius: "12px",
  };
}
