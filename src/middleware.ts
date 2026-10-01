import { defineMiddleware } from "astro:middleware";
import { securityHeaders } from "./lib/security";

export const onRequest = defineMiddleware(async (_context, next) => {
  const response = await next();
  const headers = securityHeaders(import.meta.env.DEV);
  for (const [name, value] of Object.entries(headers)) {
    response.headers.set(name, value);
  }
  return response;
});
