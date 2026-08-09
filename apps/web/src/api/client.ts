import type {ApiValidationError,User} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ACCESS_KEY = 'case_management_access';
const REFRESH_KEY = 'case_management_refresh';

export class ApiError extends Error {
  constructor(message: string, public status?: number, public kind: 'credentials'|'network'|'timeout'|'server'='server', public fieldErrors: Record<string,string>={}) { super(message); }
}

const FIELD_LABELS: Record<string,string> = {name:'שם הקבוצה',key:'מפתח השדה',label_he:'תווית בעברית',label_en:'תווית באנגלית',options_json:'ערכים לבחירה',environment_ids:'סביבות רלוונטיות'};

export function parseValidationErrors(errors: ApiValidationError[] = []): {message:string;fieldErrors:Record<string,string>} {
  const fieldErrors: Record<string,string> = {};
  for (const error of errors) {
    const field = String([...error.loc].reverse().find((part) => typeof part === 'string' && part !== 'body') || 'form');
    let message = error.msg;
    if (field === 'name' && (error.type === 'string_too_short' || error.type === 'value_error')) message = 'יש להזין שם קבוצה הכולל לפחות שני תווים';
    else if (field === 'key' && error.type === 'string_pattern_mismatch') message = 'מפתח השדה חייב להתחיל באות אנגלית קטנה ויכול להכיל אותיות באנגלית, מספרים וקו תחתון בלבד';
    else if (field === 'label_he' && error.type === 'string_too_short') message = 'יש להזין תווית בעברית';
    else if (error.type === 'missing') message = `יש להזין ${FIELD_LABELS[field] || field}`;
    else if (error.type === 'value_error') message = error.msg.replace(/^Value error,\s*/,'');
    fieldErrors[field] = message;
  }
  const messages = [...new Set(Object.values(fieldErrors))];
  return {message:messages.join(' · ') || 'יש לתקן את השדות המסומנים',fieldErrors};
}

export const token = {
  get: () => localStorage.getItem(ACCESS_KEY),
  setAccess: (access: string) => { localStorage.setItem(ACCESS_KEY, access); window.dispatchEvent(new Event('case-management-auth')); },
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
      const objectPayload = typeof payload === 'object' && payload ? payload as {detail?:unknown;errors?:ApiValidationError[]} : undefined;
      const detail = typeof objectPayload?.detail === 'string' ? objectPayload.detail : typeof objectPayload?.detail === 'object' && objectPayload.detail && 'message' in objectPayload.detail ? String((objectPayload.detail as {message:unknown}).message) : undefined;
      if (response.status === 422 && objectPayload?.errors?.length) { const parsed=parseValidationErrors(objectPayload.errors); throw new ApiError(parsed.message,422,'server',parsed.fieldErrors); }
      if (response.status === 422 && objectPayload?.detail && typeof objectPayload.detail === 'object' && 'field' in objectPayload.detail && 'message' in objectPayload.detail) { const validation=objectPayload.detail as {field:unknown;message:unknown}; throw new ApiError(String(validation.message),422,'server',{[String(validation.field)]:String(validation.message)}); }
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

export async function apiDownload(path:string):Promise<Blob>{const response=await fetch(API_URL+path,{headers:{Authorization:`Bearer ${token.get()||''}`}});if(!response.ok)throw new ApiError(`ייצוא הדוח נכשל (${response.status})`,response.status);return response.blob()}

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(API_URL + path, {
    method: 'POST', headers: { Authorization: `Bearer ${token.get() || ''}` }, body: form,
  });
  const payload = await response.json();
  if (!response.ok) throw new ApiError(payload.detail || `העלאת הקובץ נכשלה (${response.status})`, response.status);
  return payload as T;
}
