import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://www.derekdevs.com",
  trailingSlash: "never",
  integrations: [mdx(), sitemap()],
  redirects: {
    "/projects": { status: 301, destination: "/work" },
    "/projects/[slug]": { status: 301, destination: "/work/[slug]" },
    "/customer-dashboard": { status: 301, destination: "/work" },
    "/videoGameSales": { status: 301, destination: "/work" },
    "/TTRPGSentiments": { status: 301, destination: "/work" },
  },
});
