import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, FormControlLabel, Paper, Stack, Switch, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, Workflow } from '../../../../types';

export function WorkflowsTab({ environment }: { environment: Environment }) {
  const client = useQueryClient();
  const [name, setName] = useState('');
  const [asDefault, setAsDefault] = useState(false);
  const { data: items = [] } = useQuery({
    queryKey: ['workflows', environment.id],
    queryFn: () => api<Workflow[]>(`/environments/${environment.id}/workflows`),
  });
  const create = async () => {
    await api(`/environments/${environment.id}/workflows`, {
      method: 'POST', body: JSON.stringify({ name_he: name, is_default: asDefault }),
    });
    setName('');
    client.invalidateQueries({ queryKey: ['workflows', environment.id] });
  };
  const toggle = async (item: Workflow) => {
    await api(`/workflows/${item.id}`, { method: 'PATCH', body: JSON.stringify({ name_he: item.name_he, name_en: item.name_en || null, description: item.description || null, is_active: !item.is_active, is_default: item.is_default }) });
    client.invalidateQueries({ queryKey: ['workflows', environment.id] });
  };
  return <Stack spacing={2}>{items.map((item) => <Paper key={item.id} variant="outlined" sx={{ p: 2 }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between"><span><Typography fontWeight={800}>{item.name_he}</Typography><Typography color="text.secondary">{item.system_number} · {item.is_default ? 'ברירת מחדל' : 'תהליך משויך'}</Typography></span><Button onClick={() => toggle(item)}>{item.is_active ? 'השבתה' : 'הפעלה'}</Button></Stack></Paper>)}<Paper variant="outlined" sx={{ p: 2 }}><Stack spacing={2}><Typography fontWeight={800}>תהליך עבודה חדש</Typography><TextField label="שם בעברית" value={name} onChange={(event) => setName(event.target.value)} /><FormControlLabel control={<Switch checked={asDefault} onChange={(event) => setAsDefault(event.target.checked)} />} label="ברירת מחדל לסביבה" /><Button variant="contained" disabled={!name.trim()} onClick={create}>יצירה</Button></Stack></Paper></Stack>;
}
