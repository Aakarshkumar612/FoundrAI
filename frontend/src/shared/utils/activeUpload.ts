const KEY = "foundr_active_upload";

export interface StoredUpload {
  id: string;
  filename: string;
  row_count: number | null;
  is_financial: boolean;
}

export function getStoredUpload(): StoredUpload | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUpload(upload: StoredUpload): void {
  localStorage.setItem(KEY, JSON.stringify(upload));
}

export function clearStoredUpload(): void {
  localStorage.removeItem(KEY);
}
