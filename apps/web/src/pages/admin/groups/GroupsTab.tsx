import { useState } from 'react';
import { Add } from '@mui/icons-material';
import { Alert, Button, Paper, Snackbar, Stack, Typography } from '@mui/material';
import { api } from '../../../api/client';
import type { Environment, Group, Role, User } from '../../../types';
import { GroupDialog, type GroupFormValues } from './GroupDialog';
import { GroupEditor } from './GroupEditor';

export function GroupsTab({ groups, users, environments, onCreated }: { groups: Group[]; users: User[]; roles: Role[]; environments: Environment[]; onCreated: () => Promise<void> | void }) {
  const [open, setOpen] = useState(false); const [selected, setSelected] = useState<Group>(); const [saving, setSaving] = useState(false); const [error, setError] = useState(''); const [success, setSuccess] = useState(false);
  async function create(values: GroupFormValues) { setSaving(true); setError(''); try { await api('/groups', { method: 'POST', body: JSON.stringify({ ...values, description: values.description?.trim() || null, is_active: true }) }); await onCreated(); setOpen(false); setSuccess(true); } catch (caught) { setError((caught as Error).message); throw caught; } finally { setSaving(false); } }
  return <Stack spacing={2}>{error && <Alert severity="error">{error}</Alert>}<Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<Add/>} onClick={() => setOpen(true)}>קבוצה חדשה</Button>{groups.length === 0 ? <Paper sx={{ p: 5, textAlign: 'center' }}>אין קבוצות. צרו קבוצה ראשונה.</Paper> : groups.map((group) => <Paper key={group.id} variant="outlined" sx={{ p: 2, opacity: group.is_active ? 1 : .6 }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between"><span><Typography fontWeight={800}>{group.name}</Typography><Typography color="text.secondary">{group.description || 'ללא תיאור'}</Typography><Typography variant="caption">{group.member_count} חברים</Typography></span><Button onClick={() => setSelected(group)}>פתיחה</Button></Stack></Paper>)}<GroupDialog open={open} saving={saving} onClose={() => setOpen(false)} onSubmit={create}/><GroupEditor group={selected} users={users} environments={environments} onClose={() => setSelected(undefined)} onSaved={async () => { await onCreated(); setSuccess(true); }}/><Snackbar open={success} autoHideDuration={3000} onClose={() => setSuccess(false)} message="הפעולה הושלמה בהצלחה"/></Stack>;
}
