const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const token = {
  get: () => localStorage.getItem('access'),
  set: (access: string, refresh: string) => { localStorage.setItem('access', access); localStorage.setItem('refresh', refresh); },
  clear: () => localStorage.clear(),
};

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(API_URL + path, {
    ...init,
    headers: {'Content-Type': 'application/json', ...(token.get() ? {Authorization: `Bearer ${token.get()}`} : {})},
  });
  if (response.status === 401) { token.clear(); if (location.pathname !== '/login') location.href = '/login'; }
  if (!response.ok) { const error = await response.json(); throw new Error(typeof error.detail === 'string' ? error.detail : 'הפעולה נכשלה'); }
  return response.status === 204 ? undefined as T : response.json();
}
