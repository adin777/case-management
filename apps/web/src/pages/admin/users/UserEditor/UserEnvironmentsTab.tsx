import { useEffect, useState } from 'react';
import { Alert, Button, Chip, MenuItem, Stack, TextField } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, User } from '../../../../types';

type Selection = { environment_id: string };
export function UserEnvironmentsTab({ user, environments, onSaved }: { user: User; users: User[]; environments: Environment[]; onSaved: () => Promise<void> }) {
  const [rows, setRows] = useState<Selection[]>([]); const [message, setMessage] = useState('');
  useEffect(() => { setRows(user.memberships?.map((item) => ({ environment_id: item.environment_id })) || []); }, [user]);
  const ids = rows.map((row) => row.environment_id);
  async function save() { await api(`/users/${user.id}/environment-memberships`, { method: 'PUT', body: JSON.stringify(rows) }); setMessage('סביבות העבודה נשמרו'); await onSaved(); }
  return <Stack spacing={2}>{message && <Alert severity="success">{message}</Alert>}<TextField select SelectProps={{ multiple: true, renderValue: (value) => <Stack direction="row" gap={.5}>{(value as string[]).map((id) => <Chip key={id} label={environments.find((environment) => environment.id === id)?.name_he}/>)}</Stack> }} label="סביבות משויכות" value={ids} onChange={(event) => { const selected = typeof event.target.value === 'string' ? event.target.value.split(',') : event.target.value; setRows(selected.map((environment_id) => ({ environment_id }))); }}>{environments.filter((environment) => environment.is_active || ids.includes(environment.id)).map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}{!environment.is_active ? ' · לא פעילה' : ''}</MenuItem>)}</TextField><Button variant="contained" onClick={save}>שמירת סביבות</Button></Stack>;
}
