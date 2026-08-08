import { useQuery } from '@tanstack/react-query';
import { MenuItem, TextField } from '@mui/material';
import { api } from '../../../../api/client';

export function FieldValueSelector({ environmentId, fieldCode, label, value, onChange }: { environmentId: string; fieldCode: string; label: string; value: string; onChange: (value: string) => void }) {
  const { data: options = [] } = useQuery({ queryKey: ['automation-options', environmentId, fieldCode], queryFn: () => api<{ id: string; label_he: string }[]>(`/environments/${environmentId}/automation-fields/${encodeURIComponent(fieldCode)}/options`), enabled: !!fieldCode });
  if (!options.length) return <TextField label={label} value={value} onChange={(event) => onChange(event.target.value)}/>;
  return <TextField select label={label} value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <MenuItem key={option.id} value={option.id}>{option.label_he}</MenuItem>)}</TextField>;
}
