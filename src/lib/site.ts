export const site = {
  name: "Derek Shirley",
  url: "https://www.derekdevs.com",
  title: "Derek Shirley | Marketing Measurement & Analytics Engineering",
  description:
    "Derek Shirley builds the measurement teams use to decide where marketing budget goes: attribution, marketing mix models, experiments and forecasts on governed dbt and Snowflake models.",
  ogDescription:
    "Derek Shirley builds the measurement teams use to decide where marketing budget goes: attribution, marketing mix models, experiments and forecasts on governed dbt and Snowflake models.",
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
