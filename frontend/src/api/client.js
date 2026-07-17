/**
 * Tiny fetch wrapper for the Momentum API.
 *
 * - Base URL from VITE_API_BASE_URL (empty => same-origin, uses the dev proxy).
 * - `credentials: "include"` so the httpOnly session cookie rides along on
 *   every request (required for the cross-site Render deployment).
 * - Normalizes errors into a thrown `ApiError` with a readable message.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, { method = "GET", body, headers } = {}) {
  const res = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    method,
    credentials: "include",
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail =
      (data && data.detail) || (typeof data === "string" ? data : res.statusText);
    throw new ApiError(
      Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail,
      res.status
    );
  }
  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  del: (path) => request(path, { method: "DELETE" }),
};
