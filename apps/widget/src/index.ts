/**
 * Chameleon widget entry point.
 *
 * Install: <script src="https://cdn.spacechameleon.ai/w.js" data-site="abc123"></script>
 *
 * Responsibilities on load (see docs/PRD.md §3):
 *  - Read data-site from the script tag to identify the tenant.
 *  - Extract computed colors/fonts/corner-radius from the host page and build theme tokens.
 *  - Mount a Shadow DOM root so host CSS cannot break the widget and vice versa.
 *  - Render only the lightweight bubble; lazy-load the full chat bundle on first open.
 */
import { extractTheme } from "./theme/extractTheme";
import { mountBubble } from "./bubble/mountBubble";

function getCurrentScript(): HTMLScriptElement | null {
  return document.currentScript as HTMLScriptElement | null;
}

function init() {
  const script = getCurrentScript();
  const siteId = script?.dataset.site;

  if (!siteId) {
    console.error("[space-chameleon] missing data-site attribute on the widget <script> tag");
    return;
  }

  const host = document.createElement("div");
  host.id = "space-chameleon-root";
  document.body.appendChild(host);

  const shadowRoot = host.attachShadow({ mode: "open" });
  const theme = extractTheme(document.documentElement);

  mountBubble(shadowRoot, { siteId, theme });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
