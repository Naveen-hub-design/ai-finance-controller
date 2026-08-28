const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export { API_BASE_URL };

export interface ApiError extends Error {
  status: number;
  payload?: unknown;
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let payload: unknown;
    try {
      payload = await res.json();
    } catch {
      payload = undefined;
    }
    const message =
      (payload as { error?: string } | undefined)?.error ??
      `Request failed (${res.status})`;
    const err = new Error(message) as ApiError;
    err.status = res.status;
    err.payload = payload;
    throw err;
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },
  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, { method: "POST", body: JSON.stringify(body) });
  },
  put<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, { method: "PUT", body: JSON.stringify(body) });
  },
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE" });
  },
};
