import { useEffect, useState } from 'react';
import { Alert, Button, FormControlLabel, Stack, Switch, TextField } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment } from '../../../../types';

export function EnvironmentGeneralTab({ environment, onSaved }: { environment: Environment; onSaved: () => void }) {
  const [form, setForm] = useState(environment); const [message, setMessage] = useState('');
  useEffect(() => { setForm(environment); setMessage(''); }, [environment]);
  async function save() { await api(`/environments/${environment.id}`, { method: 'PATCH', body: JSON.stringify({ name_he: form.name_he, name_en: form.name_en, description: form.description, is_active: form.is_active }) }); setMessage('פרטי הסביבה נשמרו'); onSaved(); }
  return <Stack spacing={2}>{message && <Alert>{message}</Alert>}<TextField label="מספר סביבה" value={form.system_number} disabled/><TextField label="שם בעברית" value={form.name_he} onChange={e => setForm({...form,name_he:e.target.value})}/><TextField label="שם באנגלית" value={form.name_en} onChange={e => setForm({...form,name_en:e.target.value})}/><TextField label="תיאור" multiline value={form.description || ''} onChange={e => setForm({...form,description:e.target.value})}/><FormControlLabel control={<Switch checked={form.is_active} onChange={e => setForm({...form,is_active:e.target.checked})}/>} label="סביבה פעילה"/><Button variant="contained" onClick={save}>שמירה</Button></Stack>;
}
