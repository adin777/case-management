import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Checkbox, ListItemText, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment } from '../../../../types';

type AssignmentKind = 'user_id' | 'group_id' | 'department' | 'job_title';
type Option = { id: string; label: string; email?: string };
type Options = { users: Option[]; groups: Option[]; departments: string[]; job_titles: string[] };
type Rule = { id: string; name: string; conditions: { field: string; value: string | string[] }[] };
type Preview = { matched: number; users: { id: string; display_name: string; email: string; department?: string; job_title?: string }[] };
const labels: Record<AssignmentKind, string> = { user_id: 'משתמש', group_id: 'קבוצה', department: 'מחלקה', job_title: 'תפקיד ארגוני' };

export function EnvironmentAssignmentRulesTab({ environment }: { environment: Environment }) {
  const client = useQueryClient();
  const [name, setName] = useState('');
  const [field, setField] = useState<AssignmentKind>('department');
  const [values, setValues] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview>();
  const [error, setError] = useState('');
  const rulesQuery = useQuery({ queryKey: ['assignment-rules', environment.id], queryFn: () => api<Rule[]>(`/environments/${environment.id}/assignment-rules`) });
  const optionsQuery = useQuery({ queryKey: ['environment-assignment-options'], queryFn: () => api<Options>('/environment-assignment-options') });
  const options = optionsQuery.data;
  const choices = useMemo<Option[]>(() => {
    if (!options) return [];
    if (field === 'user_id') return options.users;
    if (field === 'group_id') return options.groups;
    return options[field === 'department' ? 'departments' : 'job_titles'].map(value => ({ id: value, label: value }));
  }, [field, options]);
  const payload = { name: name.trim(), conditions: [{ field, value: values }], is_active: true };

  async function show() {
    setError('');
    try { setPreview(await api<Preview>(`/environments/${environment.id}/assignment-rules/preview`, { method: 'POST', body: JSON.stringify(payload) })); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'התצוגה המקדימה נכשלה'); }
  }
  async function save() {
    setError('');
    try {
      await api(`/environments/${environment.id}/assignment-rules`, { method: 'POST', body: JSON.stringify(payload) });
      setName(''); setValues([]); setPreview(undefined);
      await client.invalidateQueries({ queryKey: ['assignment-rules', environment.id] });
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'שמירת השיוך נכשלה'); }
  }

  return <Stack spacing={2}>
    <Typography variant="h6">שיוך לפי מאפיין ארגוני</Typography>
    {(error || optionsQuery.error || rulesQuery.error) && <Alert severity="error">{error || (optionsQuery.error as Error)?.message || (rulesQuery.error as Error)?.message}</Alert>}
    {(rulesQuery.data ?? []).map(rule => <Paper key={rule.id} variant="outlined" sx={{ p: 2 }}><Typography fontWeight={800}>{rule.name}</Typography><Typography>{rule.conditions.map(condition => `${condition.field} = ${Array.isArray(condition.value) ? condition.value.join(', ') : condition.value}`).join(' וגם ')}</Typography></Paper>)}
    <Paper variant="outlined" sx={{ p: 2 }}><Stack spacing={2}>
      <TextField label="שם הכלל" value={name} onChange={event => setName(event.target.value)}/>
      <TextField select label="מקור השיוך" value={field} onChange={event => { setField(event.target.value as AssignmentKind); setValues([]); setPreview(undefined); }}>
        {(Object.keys(labels) as AssignmentKind[]).map(key => <MenuItem key={key} value={key}>{labels[key]}</MenuItem>)}
      </TextField>
      <TextField select label={`בחירת ${labels[field]}`} value={values} disabled={optionsQuery.isLoading} onChange={event => { setValues(typeof event.target.value === 'string' ? event.target.value.split(',') : event.target.value); setPreview(undefined); }} SelectProps={{ multiple: true, renderValue: selected => (selected as string[]).map(id => choices.find(option => option.id === id)?.label ?? id).join(', ') }}>
        {choices.map(option => <MenuItem key={option.id} value={option.id}><Checkbox checked={values.includes(option.id)}/><ListItemText primary={option.label} secondary={option.email}/></MenuItem>)}
      </TextField>
      <Button disabled={!name.trim() || !values.length} onClick={show}>תצוגה מקדימה</Button>
      {preview && <Alert severity="info"><Typography fontWeight={800}>נמצאו {preview.matched} עובדים</Typography>{preview.users.map(user => <Typography key={user.id} variant="body2">{user.display_name} · {user.email} · {user.department || 'ללא מחלקה'} · {user.job_title || 'ללא תפקיד'}</Typography>)}</Alert>}
      <Button variant="contained" disabled={!preview} onClick={save}>אישור והחלת השיוך</Button>
    </Stack></Paper>
  </Stack>;
}
