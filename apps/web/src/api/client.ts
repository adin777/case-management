import type {User} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ACCESS_KEY = 'case_management_access';
const REFRESH_KEY = 'case_management_refresh';

export class ApiError extends Error {
  constructor(message: string, public status?: number, public kind: 'credentials'|'network'|'timeout'|'server'='server') { super(message); }
}

export const token = {
  get: () => localStorage.getItem(ACCESS_KEY),
  set: (access: string, refresh: string) => { localStorage.setItem(ACCESS_KEY, access); localStorage.setItem(REFRESH_KEY, refresh); window.dispatchEvent(new Event('case-management-auth')); },
  clear: () => { localStorage.removeItem(ACCESS_KEY); localStorage.removeItem(REFRESH_KEY); window.dispatchEvent(new Event('case-management-auth')); },
};

export async function api<T>(path: string, init: RequestInit = {}, options: {skipAuthRedirect?: boolean} = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10_000);
  const accessToken = token.get();
  try {
    const response = await fetch(API_URL + path, {
      ...init,
      signal: controller.signal,
      headers: {'Content-Type': 'application/json', ...(accessToken ? {Authorization: `Bearer ${accessToken}`} : {}), ...init.headers},
    });
    let payload: unknown;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) payload = await response.json();
    else payload = await response.text();
    if (!response.ok) {
      const detail = typeof payload === 'object' && payload && 'detail' in payload ? String((payload as {detail:unknown}).detail) : undefined;
      if (response.status === 401 && options.skipAuthRedirect) throw new ApiError('המייל או הסיסמה אינם נכונים', 401, 'credentials');
      if (response.status === 401) { token.clear(); location.assign('/login'); }
      throw new ApiError(detail || `שגיאת שרת (${response.status})`, response.status, 'server');
    }
    return response.status === 204 ? undefined as T : payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('השרת לא הגיב בתוך 10 שניות', undefined, 'timeout');
    if (error instanceof TypeError) throw new ApiError('לא ניתן להתחבר לשרת המערכת. יש לבדוק שהשירות המקומי פועל.', undefined, 'network');
    throw error;
  } finally { window.clearTimeout(timeout); }
}

export async function login(email: string, password: string) {
  return api<{access_token:string;refresh_token:string;token_type:string}>('/auth/login', {method:'POST', body:JSON.stringify({email,password})}, {skipAuthRedirect:true});
}

export async function getCurrentUser() { return api<User>('/auth/me'); }

export async function register(display_name:string,email:string,password:string) {
  return api<{access_token:string;refresh_token:string;token_type:string}>('/auth/register',{method:'POST',body:JSON.stringify({display_name,email,password})},{skipAuthRedirect:true});
}
