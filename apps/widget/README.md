# Chameleon widget

Preact + TypeScript + Vite, rendered inside Shadow DOM. Builds to a single
`w.js` IIFE served from CloudFront.

```bash
npm install
npm run dev      # local dev server with a demo host page
npm run build    # emits dist/w.js
```

Budget: loader < 15 KB gzipped (PRD §5 NFR). Run `npm run build` and check
`dist/w.js.gz` size before merging any change here.
