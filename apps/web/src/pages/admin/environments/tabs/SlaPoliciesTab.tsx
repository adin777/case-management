import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, SlaPolicy } from '../../../../types';

export function SlaPoliciesTab({ environment }: { environment: Environment }) {
  const client = useQueryClient();
  const [name, setName] = useState('');
  const [response, setResponse] = useState(30);
  const [resolution, setResolution] = useState(240);
  const { data: items = [] } = useQuery({ queryKey: ['sla', environment.id], queryFn: () => api<SlaPolicy[]>(`/environments/${environment.id}/sla-policies`) });
  const create = async () => {
    await api(`/environments/${environment.id}/sla-policies`, { method: 'POST', body: JSON.stringify({ name_he: name, response_minutes: response, resolution_minutes: resolution, warning_threshold_percent: 80, is_active: true }) });
    setName(''); client.invalidateQueries({ queryKey: ['sla', environment.id] });
  };
  return <Stack spacing={2}>{items.map((item) => <Paper key={item.id} variant="outlined" sx={{ p: 2 }}><Typography fontWeight={800}>{item.name_he}</Typography><Typography color="text.secondary">תגובה תוך {item.response_minutes} דקות · פתרון תוך {item.resolution_minutes} דקות</Typography></Paper>)}<Paper variant="outlined" sx={{ p: 2 }}><Stack spacing={2}><Typography fontWeight={800}>מדיניות SLA חדשה</Typography><TextField label="שם המדיניות" value={name} onChange={(event) => setName(event.target.value)} /><Stack direction={{ xs: 'column', sm: 'row' }} gap={2}><TextField fullWidth type="number" label="תגובה בדקות" value={response} onChange={(event) => setResponse(Number(event.target.value))} /><TextField fullWidth type="number" label="פתרון בדקות" value={resolution} onChange={(event) => setResolution(Number(event.target.value))} /></Stack><Typography>תצוגה מקדימה: תגובה תוך {response} דקות, פתרון תוך {resolution} דקות</Typography><Button variant="contained" disabled={!name || response < 1 || resolution < 1} onClick={create}>יצירת מדיניות</Button></Stack></Paper></Stack>;
}
