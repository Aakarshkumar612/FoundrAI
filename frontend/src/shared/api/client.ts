import { getAccessToken } from "@/shared/auth/supabase";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message ?? err?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get:    <T>(path: string)               => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

export async function streamQuery(
  question: string,
  uploadId: string | null,
  onEvent: (event: string, data: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = await getAccessToken();
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ question, upload_id: uploadId }),
    signal,
  });
  if (!res.ok) throw new Error(`Stream error: ${res.status}`);
  const reader = res.body!.getReader();
  const dec = new TextDecoder();
  let buf = "", currentEvent = "message";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("event:")) { currentEvent = line.slice(6).trim(); }
      else if (line.startsWith("data:")) { onEvent(currentEvent, line.slice(5).trim()); currentEvent = "message"; }
    }
  }
}
