import {beforeEach,describe,expect,it} from 'vitest';
const storage=new Map<string,string>();
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(key:string)=>storage.get(key)??null,setItem:(key:string,value:string)=>storage.set(key,value),removeItem:(key:string)=>storage.delete(key),clear:()=>storage.clear()},configurable:true});
const root={lang:'',dir:''};Object.defineProperty(globalThis,'document',{value:{documentElement:root},configurable:true});
const module=await import('./index');const {default:i18n,applyLanguage,localized,LANGUAGE_KEY}=module;

describe('application languages',()=>{
  beforeEach(()=>storage.clear());
  it('switches Hebrew/English and persists the preference',async()=>{await applyLanguage('en');expect(i18n.language).toBe('en');expect(root.dir).toBe('ltr');expect(localStorage.getItem(LANGUAGE_KEY)).toBe('en');await applyLanguage('he');expect(root.dir).toBe('rtl')});
  it('uses English labels and falls back to Hebrew',()=>{expect(localized('סביבה','Environment','en')).toBe('Environment');expect(localized('סביבה','', 'en')).toBe('סביבה')});
  it('translates required validation in both languages',async()=>{await i18n.changeLanguage('he');expect(i18n.t('common.required')).toBe('שדה חובה');await i18n.changeLanguage('en');expect(i18n.t('common.required')).toBe('Required field')});
});
