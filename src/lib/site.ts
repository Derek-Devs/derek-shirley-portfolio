export const site = {
  name: "Derek Shirley",
  url: "https://derekdevs.com",
  title: "Derek Shirley | Marketing Measurement & Analytics Engineering",
  description:
    "Derek Shirley helps marketing teams see what’s working and where to spend next, with attribution, mix models, experiments and forecasts on dbt and Snowflake.",
  ogDescription:
    "Derek Shirley helps marketing teams see what’s working and where to spend next, with attribution, mix models, experiments and forecasts on dbt and Snowflake.",
  email: "derek@derekdevs.com",
  location: "Dallas-Fort Worth, Texas",
  github: "https://github.com/Derek-Devs",
  linkedin: "https://www.linkedin.com/in/derekdevs/",
  resume: "/Derek_Shirley_Resume.pdf",
  themeColor: "#f6f3ed",
  darkThemeColor: "#171c19",
} as const;

export function formatDateRange(
  start: { label: string },
  end?: { label: string },
) {
  return end ? `${start.label} to ${end.label}` : `${start.label} to present`;
}

// The page's public path. The build writes /work.html, so Astro.url.pathname
// ends in .html, but the site serves and links to /work.
export function pagePath(pathname: string) {
  return pathname.replace(/(?:\/index)?\.html$/, "").replace(/\/$/, "") || "/";
}

export function canonicalUrl(pathname: string) {
  const path = pagePath(pathname);
  return `${site.url}${path === "/" ? "" : path}`;
}

export function workHref(item: {
  href?: string;
  github?: string;
  demo?: string;
}) {
  return item.href ?? item.github ?? item.demo;
}

export function workIsExternal(item: {
  href?: string;
  github?: string;
  demo?: string;
}) {
  const href = workHref(item);
  return Boolean(href && /^https?:\/\//.test(href));
}
