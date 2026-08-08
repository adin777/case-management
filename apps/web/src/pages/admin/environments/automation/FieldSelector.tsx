import { MenuItem, TextField } from '@mui/material';
import type { AutomationField } from './types';

export function FieldSelector({ label, fields, value, onChange }: { label: string; fields: AutomationField[]; value: string; onChange: (value: string) => void }) {
  return <TextField select label={label} value={value} onChange={(event) => onChange(event.target.value)}>{fields.map((field) => <MenuItem key={field.code} value={field.code}>{field.label_he}</MenuItem>)}</TextField>;
}
