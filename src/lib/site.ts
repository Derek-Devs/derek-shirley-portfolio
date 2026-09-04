export const site = {
  name: "Derek Shirley",
  url: "https://www.derekdevs.com",
  title: "Derek Shirley | Decision Science, Growth, and Data Systems",
  description:
    "Derek Shirley's work in decision science, growth measurement, product analytics, analytics engineering, and data systems.",
  ogDescription:
    "Decision science, growth measurement, and data systems.",
  email: "derek@derekdevs.com",
  location: "Dallas-Fort Worth, Texas",
  github: "https://github.com/Derek-Devs",
  linkedin: "https://www.linkedin.com/in/derekdevs/",
  themeColor: "#111315",
} as const;

export function formatDateRange(
  start: { label: string },
  end?: { label: string },
) {
  return end ? `${start.label} to ${end.label}` : `${start.label} to present`;
}

export function canonicalUrl(pathname: string) {
  const path = pathname === "/" ? "" : pathname.replace(/\/$/, "");
  return `${site.url}${path}`;
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
