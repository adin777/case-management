import {beforeEach,describe,expect,it,vi} from 'vitest';

const storage=new Map<string,string>();
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(key:string)=>storage.get(key)??null,setItem:(key:string,value:string)=>storage.set(key,value),removeItem:(key:string)=>storage.delete(key)}});
Object.defineProperty(globalThis,'window',{value:{setTimeout,clearTimeout,dispatchEvent:vi.fn()}});
const {getCurrentUser,login,parseValidationErrors,register,token}=await import('./client');

describe('authentication client',()=>{
  beforeEach(()=>{storage.clear();vi.restoreAllMocks()});
  it('submits login payload and returns tokens',async()=>{globalThis.fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({access_token:'a',refresh_token:'r',token_type:'bearer'}),{status:200,headers:{'content-type':'application/json'}}));const result=await login('admin@example.com','Admin123!');expect(result.access_token).toBe('a');expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/login',expect.objectContaining({method:'POST',body:JSON.stringify({email:'admin@example.com',password:'Admin123!'})}))});
  it('maps invalid credentials without redirecting',async()=>{globalThis.fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Invalid credentials'}),{status:401,headers:{'content-type':'application/json'}}));await expect(login('a@b.com','wrong')).rejects.toMatchObject({kind:'credentials',status:401})});
  it('maps an unavailable backend',async()=>{globalThis.fetch=vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));await expect(login('a@b.com','Password1')).rejects.toEqual(expect.objectContaining({kind:'network'}))});
  it('stores only application tokens and retrieves current user',async()=>{token.set('access','refresh');expect(storage.size).toBe(2);globalThis.fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'1',email:'a@b.com',display_name:'A',is_system_admin:false}),{status:200,headers:{'content-type':'application/json'}}));expect((await getCurrentUser()).email).toBe('a@b.com');token.clear();expect(storage.size).toBe(0)});
  it('submits registration payload',async()=>{globalThis.fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({access_token:'a',refresh_token:'r',token_type:'bearer'}),{status:201,headers:{'content-type':'application/json'}}));await register('New User','new@example.com','Password1');expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/register',expect.objectContaining({body:JSON.stringify({display_name:'New User',email:'new@example.com',password:'Password1'})}))});
  it('parses FastAPI field validation details into Hebrew field errors',()=>{const parsed=parseValidationErrors([{type:'string_too_short',loc:['body','name'],msg:'String too short'}]);expect(parsed.fieldErrors.name).toContain('לפחות שני תווים');expect(parsed.message).not.toBe('Validation failed')});
});
