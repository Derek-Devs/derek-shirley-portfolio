export const site = {
  name: "Derek Shirley",
  url: "https://www.derekdevs.com",
  title: "Derek Shirley | Marketing Analytics & Growth Measurement",
  description:
    "Derek Shirley leads marketing analytics at Lark Health. Read about his work in attribution, enrollment forecasting, marketing budgets, and pricing analytics.",
  ogDescription:
    "Marketing analytics at Lark Health, with projects in attribution, enrollment forecasting, and budget planning.",
  email: "derek@derekdevs.com",
  location: "Dallas-Fort Worth, Texas",
  github: "https://github.com/Derek-Devs",
  linkedin: "https://www.linkedin.com/in/derekdevs/",
  resume: "/Derek_Shirley_Resume_2026.pdf",
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
