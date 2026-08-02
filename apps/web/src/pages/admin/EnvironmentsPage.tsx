import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Add, Settings } from '@mui/icons-material';
import { Alert, Box, Button, Card, CardContent, Checkbox, Container, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Grid, MenuItem, Paper, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Environment, RequestType, User, UserField } from '../../types';

type FieldSelection = { definition: UserField; selection?: { user_field_definition_id: string; is_visible: boolean; is_required: boolean; is_editable_by_user: boolean; is_editable_by_environment_admin: boolean; sort_order: number } };
type AutomationRule = { id: string; name: string; description?: string; trigger_type: string; is_active: boolean };

export function EnvironmentsPage() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Environment>();
  const [tab, setTab] = useState(0);
  const [message, setMessage] = useState('');
  const [ruleName, setRuleName] = useState('');
  const [ruleTrigger, setRuleTrigger] = useState('case_created');
  const [form, setForm] = useState({ code: '', name_he: '', name_en: '', description: '' });
  const [fieldRows, setFieldRows] = useState<FieldSelection[]>([]);
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: types = [] } = useQuery({ queryKey: ['request-types', selected?.id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${selected!.id}`), enabled: !!selected });
  const { data: availableFields = [] } = useQuery({ queryKey: ['environment-user-fields', selected?.id], queryFn: () => api<FieldSelection[]>(`/environments/${selected!.id}/user-fields`), enabled: !!selected && tab === 1 });
  const { data: rules = [] } = useQuery({ queryKey: ['automation-rules', selected?.id], queryFn: () => api<AutomationRule[]>(`/automation-rules?environment_id=${selected!.id}`), enabled: !!selected && tab === 2 });
  useEffect(() => setFieldRows(availableFields), [availableFields]);

  async function createEnvironment() {
    await api('/environments', { method: 'POST', body: JSON.stringify(form) });
    setOpen(false); client.invalidateQueries({ queryKey: ['environments'] });
  }
  function changeField(index: number, key: string, value: boolean) {
    setFieldRows((rows) => rows.map((row, current) => current === index ? {
      ...row,
      selection: {
        user_field_definition_id: row.definition.id,
        is_visible: row.selection?.is_visible ?? true,
        is_required: row.selection?.is_required ?? false,
        is_editable_by_user: row.selection?.is_editable_by_user ?? false,
        is_editable_by_environment_admin: row.selection?.is_editable_by_environment_admin ?? true,
        sort_order: row.selection?.sort_order ?? index,
        [key]: value,
      },
    } : row));
  }
  async function saveFields() {
    if (!selected) return;
    await api(`/environments/${selected.id}/user-fields`, { method: 'PUT', body: JSON.stringify(fieldRows.filter((row) => row.selection?.is_visible).map((row) => row.selection)) });
    setMessage('שדות המשתמש נשמרו בהצלחה');
    client.invalidateQueries({ queryKey: ['environment-user-fields', selected.id] });
  }
  async function createRule() {
    if (!selected || !ruleName.trim()) return;
    await api('/automation-rules', { method: 'POST', body: JSON.stringify({ environment_id: selected.id, name: ruleName, trigger_type: ruleTrigger, conditions_json: {}, actions_json: [], priority: rules.length }) });
    setRuleName(''); setMessage('כלל האוטומציה נוצר'); client.invalidateQueries({ queryKey: ['automation-rules', selected.id] });
  }

  return <Container maxWidth="xl"><Stack spacing={3}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}>
      <Box><Typography variant="h4" fontWeight={800}>סביבות עבודה</Typography><Typography color="text.secondary">ניהול הגדרות, סוגי קריאות ושדות משתמש לכל סביבה</Typography></Box>
      {me?.is_system_admin && <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>סביבה חדשה</Button>}
    </Stack>
    {message && <Alert severity="success" onClose={() => setMessage('')}>{message}</Alert>}
    <Grid container spacing={2}>{environments.map((environment) => <Grid size={{ xs: 12, md: 4 }} key={environment.id}><Card onClick={() => { setSelected(environment); setTab(0); }} sx={{ cursor: 'pointer', border: selected?.id === environment.id ? '2px solid' : undefined, borderColor: 'primary.main' }}><CardContent><Stack direction="row" spacing={1.5}><Settings color="primary" /><Box><Typography variant="h6">{environment.name_he}</Typography><Typography color="text.secondary">{environment.name_en} · {environment.code}</Typography><Typography>{environment.description}</Typography></Box></Stack></CardContent></Card></Grid>)}</Grid>
    {selected && <Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)}><Tab label="סוגי קריאות" /><Tab label="שדות משתמש" /><Tab label="כללים אוטומטיים" /></Tabs><Box sx={{ p: 3 }}>
      {tab === 0 && <Stack spacing={1}>{types.length ? types.map((type) => <Paper key={type.id} variant="outlined" sx={{ p: 2 }}><Typography fontWeight={700}>{type.name_he}</Typography><Typography color="text.secondary">{type.is_active ? 'פעיל' : 'מושבת'}</Typography></Paper>) : <Typography color="text.secondary">אין סוגי קריאות בסביבה זו</Typography>}</Stack>}
      {tab === 1 && <Stack spacing={2}>{fieldRows.length === 0 ? <Typography color="text.secondary">מנהל המערכת טרם יצר שדות משתמש גלובליים</Typography> : fieldRows.map((row, index) => <Paper key={row.definition.id} variant="outlined" sx={{ p: 2 }}><Typography fontWeight={700}>{row.definition.label_he}</Typography><Typography variant="body2" color="text.secondary">{row.definition.key} · {row.definition.field_type}</Typography><Stack direction={{ xs: 'column', md: 'row' }}><FormControlLabel control={<Checkbox checked={Boolean(row.selection?.is_visible)} onChange={(event) => changeField(index, 'is_visible', event.target.checked)} />} label="הצגה בסביבה" /><FormControlLabel control={<Checkbox checked={Boolean(row.selection?.is_required)} onChange={(event) => changeField(index, 'is_required', event.target.checked)} />} label="חובה" /><FormControlLabel control={<Checkbox checked={Boolean(row.selection?.is_editable_by_user)} onChange={(event) => changeField(index, 'is_editable_by_user', event.target.checked)} />} label="עריכה עצמית" /><FormControlLabel control={<Checkbox checked={row.selection?.is_editable_by_environment_admin ?? true} onChange={(event) => changeField(index, 'is_editable_by_environment_admin', event.target.checked)} />} label="עריכה על ידי מנהל סביבה" /></Stack></Paper>)}<Button variant="contained" onClick={saveFields} disabled={!fieldRows.length}>שמירת בחירת שדות</Button></Stack>}
      {tab === 2 && <Stack spacing={2}><Typography color="text.secondary">תשתית בסיסית לכללים — ללא עורך Drag & Drop</Typography>{rules.map((rule) => <Paper key={rule.id} variant="outlined" sx={{ p: 2 }}><Typography fontWeight={700}>{rule.name}</Typography><Typography variant="body2">Trigger: {rule.trigger_type}</Typography></Paper>)}<Stack direction={{ xs: 'column', md: 'row' }} spacing={1}><TextField fullWidth label="שם הכלל" value={ruleName} onChange={(event) => setRuleName(event.target.value)} /><TextField select fullWidth label="Trigger" value={ruleTrigger} onChange={(event) => setRuleTrigger(event.target.value)}>{['case_created','case_status_changed','case_priority_changed','participant_added'].map((trigger) => <MenuItem key={trigger} value={trigger}>{trigger}</MenuItem>)}</TextField><Button variant="contained" disabled={!ruleName.trim()} onClick={createRule}>יצירת כלל</Button></Stack></Stack>}
    </Box></Paper>}
  </Stack>
  <Dialog open={open} onClose={() => setOpen(false)} fullWidth><DialogTitle>סביבה חדשה</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>{(['code', 'name_he', 'name_en', 'description'] as const).map((key) => <TextField key={key} label={{ code: 'קוד', name_he: 'שם בעברית', name_en: 'שם באנגלית', description: 'תיאור' }[key]} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />)}</Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)}>ביטול</Button><Button variant="contained" onClick={createEnvironment}>יצירה</Button></DialogActions></Dialog>
  </Container>;
}
