import type { MetadataRoute } from "next";

/** P7-01: installable shell + `public/sw.js` (registered in prod from `ServiceWorkerRegister`). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NyayaSetu — AI Legal Companion",
    short_name: "NyayaSetu",
    description: "Draft documents, understand your issue, and get practical next steps.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#78350f",
    orientation: "portrait-primary",
    categories: ["legal", "productivity", "utilities"],
    icons: [
      {
        src: "/next.svg",
        type: "image/svg+xml",
        sizes: "any",
        purpose: "any",
      },
    ],
  };
}
