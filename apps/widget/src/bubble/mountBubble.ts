import { render } from "preact";
import type { ThemeTokens } from "../theme/extractTheme";
import { Bubble } from "./Bubble";

export interface MountOptions {
  siteId: string;
  theme: ThemeTokens;
}

export function mountBubble(shadowRoot: ShadowRoot, options: MountOptions) {
  const container = document.createElement("div");
  shadowRoot.appendChild(container);
  render(<Bubble {...options} />, container);
}
