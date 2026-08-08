import { MenuItem, TextField } from '@mui/material';

export function ApprovalPolicySelector({ value, onChange }: { value: string; onChange: (value: 'all_active_steps' | 'highest_active_step') => void }) {
  return <TextField select label="מדיניות אישור" value={value} onChange={(event) => onChange(event.target.value as 'all_active_steps' | 'highest_active_step')}><MenuItem value="all_active_steps">כולם חייבים לאשר</MenuItem><MenuItem value="highest_active_step">מספיק אישור השלב הפעיל הגבוה ביותר</MenuItem></TextField>;
}
