import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, Priority, User, Workflow } from '../../../../types';
import type { SystemField, SystemFieldOption } from './types';

const blank = { label_he: '', description: '', color: '#64748b', sort_order: 0, is_active: true, is_initial: false, is_final: false, workflow_id: '', requires_approval: false, default_priority_id: '', default_sub_priority_id: '', default_assignee_user_id: '', default_assignee_group_id: '' };

export function SystemFieldValuesDialog({ environment, field, onClose }: { environment: Environment; field?: SystemField; onClose: () => void }) {
  const client = useQueryClient(); const [editing, setEditing] = useState<SystemFieldOption>(); const [form, setForm] = useState(blank);
  const { data: workflows = [] } = useQuery({ queryKey: ['workflows', environment.id], queryFn: () => api<Workflow[]>(`/environments/${environment.id}/workflows`) });
  const { data: priorities = [] } = useQuery({ queryKey: ['priorities', environment.id], queryFn: () => api<Priority[]>(`/environments/${environment.id}/priorities`) });
  const { data: subs = [] } = useQuery({ queryKey: ['sub-priorities', environment.id], queryFn: () => api<SystemFieldOption[]>(`/environments/${environment.id}/sub-priorities`) });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  useEffect(() => { setEditing(undefined); setForm(blank); }, [field]);
  const choose = (item: SystemFieldOption) => { setEditing(item); setForm({ ...blank, ...item, workflow_id: item.workflow_id || '', default_priority_id: item.default_priority_id || '', default_sub_priority_id: item.default_sub_priority_id || '', default_assignee_user_id: item.default_assignee_user_id || '', default_assignee_group_id: item.default_assignee_group_id || '' }); };
  async function save() {
    if (!field) return;
    const code = `value_${Date.now()}`;
    if (field.code === 'request_type') {
      const body = { environment_id: environment.id, code, name_he: form.label_he, name_en: form.label_he, description: form.description || null, is_active: form.is_active, sort_order: form.sort_order, requires_approval: form.requires_approval, workflow_definition_id: form.workflow_id || null, default_priority_id: form.default_priority_id || null, default_sub_priority_id: form.default_sub_priority_id || null, default_assignee_user_id: form.default_assignee_user_id || null, default_assignee_group_id: form.default_assignee_group_id || null };
      await api(editing ? `/request-types/${editing.id}` : '/request-types', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(body) });
    } else if (field.code === 'status') {
      const body = { code, label_he: form.label_he, label_en: form.label_he, description: form.description || null, color: form.color, sort_order: form.sort_order, is_initial: form.is_initial, is_final: form.is_final, is_closed: form.is_final, is_active: form.is_active };
      await api(editing ? `/workflow-statuses/${editing.id}` : `/workflows/${form.workflow_id}/statuses`, { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(body) });
    } else {
      const body = { code, label_he: form.label_he, label_en: form.label_he, description: form.description || null, color: form.color, sort_order: form.sort_order, is_active: form.is_active };
      const path = field.code === 'priority' ? (editing ? `/environments/${environment.id}/priorities/${editing.id}` : `/environments/${environment.id}/priorities`) : (editing ? `/sub-priorities/${editing.id}` : `/environments/${environment.id}/sub-priorities`);
      await api(path, { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(body) });
    }
    setEditing(undefined); setForm(blank); await client.invalidateQueries({ queryKey: ['system-fields', environment.id] });
  }
  return <Dialog open={!!field} onClose={onClose} fullWidth maxWidth="md"><DialogTitle>ניהול ערכי {field?.label_he}</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
    {field?.options.map((item) => <Paper key={item.id} variant="outlined" sx={{ p: 1.5 }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }}><span><Typography fontWeight={800}>{item.label_he}</Typography><Typography variant="body2" color="text.secondary">{item.is_active === false ? 'מושבת' : 'פעיל'} · סדר {item.sort_order || 0}</Typography></span><Button onClick={() => choose(item)}>עריכה</Button></Stack></Paper>)}
    <Typography fontWeight={800}>{editing ? 'עריכת ערך' : 'ערך חדש'}</Typography><TextField label="שם" value={form.label_he} onChange={(event) => setForm({ ...form, label_he: event.target.value })}/><TextField label="תיאור" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })}/><TextField type="number" label="סדר" value={form.sort_order} onChange={(event) => setForm({ ...form, sort_order: Number(event.target.value) })}/>
    {field?.code !== 'request_type' && <TextField type="color" label="צבע" value={form.color} onChange={(event) => setForm({ ...form, color: event.target.value })}/>}<FormControlLabel control={<Switch checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })}/>} label="פעיל"/>
    {field?.code === 'status' && <><TextField select label="תהליך עבודה" value={form.workflow_id} disabled={!!editing} onChange={(event) => setForm({ ...form, workflow_id: event.target.value })}>{workflows.filter((item) => item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.name_he}</MenuItem>)}</TextField><FormControlLabel control={<Switch checked={form.is_initial} onChange={(event) => setForm({ ...form, is_initial: event.target.checked })}/>} label="סטטוס התחלתי"/><FormControlLabel control={<Switch checked={form.is_final} onChange={(event) => setForm({ ...form, is_final: event.target.checked })}/>} label="סטטוס סופי"/></>}
    {field?.code === 'request_type' && <><TextField select label="תהליך עבודה" value={form.workflow_id} onChange={(event) => setForm({ ...form, workflow_id: event.target.value })}><MenuItem value="">ללא</MenuItem>{workflows.filter((item) => item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.name_he}</MenuItem>)}</TextField><TextField select label="עדיפות ברירת מחדל" value={form.default_priority_id} onChange={(event) => setForm({ ...form, default_priority_id: event.target.value })}><MenuItem value="">ללא</MenuItem>{priorities.filter((item) => item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.label_he}</MenuItem>)}</TextField><TextField select label="תת-עדיפות ברירת מחדל" value={form.default_sub_priority_id} onChange={(event) => setForm({ ...form, default_sub_priority_id: event.target.value })}><MenuItem value="">ללא</MenuItem>{subs.filter((item) => item.is_active !== false).map((item) => <MenuItem key={item.id} value={item.id}>{item.label_he}</MenuItem>)}</TextField><TextField select label="מטפל ברירת מחדל" value={form.default_assignee_user_id} onChange={(event) => setForm({ ...form, default_assignee_user_id: event.target.value })}><MenuItem value="">ללא</MenuItem>{users.filter((item) => item.is_active !== false).map((item) => <MenuItem key={item.id} value={item.id}>{item.display_name}</MenuItem>)}</TextField><FormControlLabel control={<Switch checked={form.requires_approval} onChange={(event) => setForm({ ...form, requires_approval: event.target.checked })}/>} label="דורש סבב אישורים"/></>}
  </Stack></DialogContent><DialogActions><Button onClick={onClose}>סגירה</Button><Button variant="contained" disabled={!form.label_he.trim() || (field?.code === 'status' && !form.workflow_id)} onClick={save}>שמירה</Button></DialogActions></Dialog>;
}
