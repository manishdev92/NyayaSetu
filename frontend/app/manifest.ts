import type { MetadataRoute } from "next";

/** P7-01: installable shell + `public/sw.js` (registered in prod from `ServiceWorkerRegister`). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NyayaSetu — Legal clarity for India",
    short_name: "NyayaSetu",
    description: "Legal clarity for India — structured guidance and drafting help. Educational, not a law firm.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#78350f",
    orientation: "portrait-primary",
    categories: ["legal", "productivity", "utilities"],
    icons: [
      {
        src: "/icon.svg",
        type: "image/svg+xml",
        sizes: "any",
        purpose: "any",
      },
    ],
  };
}
