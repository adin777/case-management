export function displayCaseNumber(value?: string) {
  return (value || '').replace(/^CASE-/i, '');
}

export function formatCaseDate(value?: string) {
  return value ? new Date(value).toLocaleString('he-IL') : 'לא זמין';
}
