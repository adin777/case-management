import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import he from './locales/he.json';
import en from './locales/en.json';

export const LANGUAGE_KEY = 'case_management_language';
export type AppLanguage = 'he' | 'en';
const initialLanguage: AppLanguage = typeof localStorage !== 'undefined' && localStorage.getItem(LANGUAGE_KEY) === 'en' ? 'en' : 'he';

void i18n.use(initReactI18next).init({
  resources: { he: { translation: he }, en: { translation: en } },
  lng: initialLanguage,
  fallbackLng: 'he',
  interpolation: { escapeValue: false },
});

export function applyLanguage(language: AppLanguage) {
  if(typeof localStorage!=='undefined')localStorage.setItem(LANGUAGE_KEY, language);
  if(typeof document!=='undefined'){document.documentElement.lang = language;document.documentElement.dir = language === 'he' ? 'rtl' : 'ltr'}
  return i18n.changeLanguage(language);
}

if(typeof document!=='undefined'){document.documentElement.lang = initialLanguage;document.documentElement.dir = initialLanguage === 'he' ? 'rtl' : 'ltr'}

export function localized(hebrew: string, english: string | null | undefined, language = i18n.language) {
  return language === 'en' && english?.trim() ? english : hebrew;
}

export default i18n;
