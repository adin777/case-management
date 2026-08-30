import { Chip } from '@mui/material';

export function BusinessPill({ label, kind = 'status' }: { label?: string; kind?: 'status' | 'priority' }) {
  const text = label || 'לא הוגדר';
  const lower = text.toLowerCase();
  const color = kind === 'priority'
    ? (/גבוה|דחוף|high|urgent/.test(lower) ? 'error' : /בינוני|medium/.test(lower) ? 'warning' : 'info')
    : (/סגור|נפתר|closed|resolved|אושר/.test(lower) ? 'success' : /נדחה|בוטל|rejected|cancel/.test(lower) ? 'error' : /ממתין|waiting/.test(lower) ? 'warning' : 'info');
  return <Chip size="small" color={color} variant="outlined" label={text} sx={{ bgcolor: `${color}.50`, borderRadius: 1.75 }}/>; 
}
