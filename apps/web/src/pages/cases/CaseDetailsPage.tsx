import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Lock, LockOpen, PersonAdd, Send } from '@mui/icons-material';
import { Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, Container, Divider, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Stack, TextField, Tooltip, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Case, Comment, Participant, Priority, RequestType, SubPriority, User } from '../../types';
import { statusLabel } from '../../status';
import { CaseAttachments } from './details/CaseAttachments';
import { CaseLockDialog } from './details/CaseLockDialog';
import { InlineTextField } from './details/InlineTextField';

type StatusOption = { id: string; label_he: string; current: boolean; allowed: boolean; reason?: string };

function Feed({ rows, me }: { rows: Comment[]; me?: User }) {
  if (!rows.length) return <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>עדיין אין הודעות בשיחה</Box>;
  return <Stack spacing={1.5}>{rows.map((row) => <Box key={row.id} sx={{ display: 'flex', gap: 1, flexDirection: row.author_id === me?.id ? 'row-reverse' : 'row' }}><Avatar>{row.author_name?.[0] || 'מ'}</Avatar><Paper variant="outlined" sx={{ p: 1.5, maxWidth: '82%' }}><Typography variant="caption" fontWeight={700}>{row.author_name || 'משתמש'}</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{row.body}</Typography><Typography variant="caption" color="text.secondary">{new Date(row.created_at).toLocaleString('he-IL')}</Typography></Paper></Box>)}</Stack>;
}

export function CaseDetailsPage() {
  const { id } = useParams(); const qc = useQueryClient();
  const [body, setBody] = useState(''); const [participantId, setParticipantId] = useState('');
  const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [lockOpen, setLockOpen] = useState(false);
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: item, isLoading } = useQuery({ queryKey: ['case', id], queryFn: () => api<Case>(`/cases/${id}`) });
  const enabled = !!item;
  const { data: types = [] } = useQuery({ queryKey: ['request-types', item?.environment_id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${item!.environment_id}`), enabled });
  const { data: priorities = [] } = useQuery({ queryKey: ['priorities', item?.environment_id], queryFn: () => api<Priority[]>(`/environments/${item!.environment_id}/priorities`), enabled });
  const { data: subs = [] } = useQuery({ queryKey: ['sub-priorities', item?.environment_id], queryFn: () => api<SubPriority[]>(`/environments/${item!.environment_id}/sub-priorities`), enabled });
  const { data: statuses = [] } = useQuery({ queryKey: ['status-options', id, item?.workflow_status_id], queryFn: () => api<StatusOption[]>(`/cases/${id}/status-options`), enabled });
  const { data: participants = [] } = useQuery({ queryKey: ['participants', id], queryFn: () => api<Participant[]>(`/cases/${id}/participants`), enabled });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: comments = [] } = useQuery({ queryKey: ['public-comments', id], queryFn: () => api<Comment[]>(`/cases/${id}/public-comments`), enabled });
  const candidates = useMemo(() => users.filter((user) => user.is_active !== false && !participants.some((row) => row.user_id === user.id)), [users, participants]);
  const refresh = () => qc.invalidateQueries({ queryKey: ['case', id] });
  async function patch(payload: object) { try { await api(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify({ ...payload, version: item!.version }) }); setSuccess('השינוי נשמר'); await refresh(); } catch (caught) { setError((caught as Error).message); throw caught; } }
  async function transition(workflow_status_id: string) { try { await api(`/cases/${id}/transitions`, { method: 'POST', body: JSON.stringify({ workflow_status_id }) }); await refresh(); } catch (caught) { setError((caught as Error).message); } }
  async function addParticipant() { await api(`/cases/${id}/participants`, { method: 'POST', body: JSON.stringify({ user_id: participantId, participant_type: 'participant' }) }); setParticipantId(''); qc.invalidateQueries({ queryKey: ['participants', id] }); }
  const send = useMutation({ mutationFn: () => api(`/cases/${id}/public-comments`, { method: 'POST', body: JSON.stringify({ body }) }), onSuccess: () => { setBody(''); qc.invalidateQueries({ queryKey: ['public-comments', id] }); }, onError: (caught) => setError((caught as Error).message) });
  async function saveLock(reason: string) { await api(`/cases/${id}/lock`, { method: 'POST', body: JSON.stringify({ locked: !item!.is_locked, reason: reason || null, version: item!.version }) }); setLockOpen(false); await refresh(); }
  if (isLoading || !item) return <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 400 }}><CircularProgress/></Box>;
  const editable = item.permissions.can_edit;
  const currentStatus = statuses.find((row) => row.current)?.label_he || statusLabel(item.status);
  return <Box sx={{ minHeight: '100%', bgcolor: '#f5f7fb', py: 3 }}><Container maxWidth="xl"><Stack spacing={2.5}>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}{success && <Alert severity="success" onClose={() => setSuccess('')}>{success}</Alert>}
    <Paper elevation={0} sx={{ p: { xs: 2, md: 3 }, border: '1px solid #dce3ef', borderRadius: 3, background: 'linear-gradient(135deg,#fff,#eef4ff)' }}><Typography color="primary" fontWeight={800}>{item.case_number}</Typography><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Box sx={{ flex: 1 }}><InlineTextField label="נושא" value={item.title} editable={editable} onSave={(title) => patch({ title })}/><Typography color="text.secondary" variant="body2">פותח: {item.reporter_name || '—'} · {item.reporter_email || '—'} · {new Date(item.created_at).toLocaleDateString('he-IL')}</Typography></Box><Stack direction="row" gap={1} flexWrap="wrap"><Chip color="primary" label={currentStatus}/><Chip variant="outlined" label={priorities.find((row) => row.id === item.priority_id)?.label_he || item.priority}/>{item.is_locked && <Chip color="warning" icon={<Lock/>} label="נעולה לשינויים"/>}{item.permissions.can_lock && <Button variant="outlined" color="warning" startIcon={item.is_locked ? <LockOpen/> : <Lock/>} onClick={() => setLockOpen(true)}>{item.is_locked ? 'פתיחת נעילה' : 'נעילת קריאה'}</Button>}</Stack></Stack></Paper>
    {item.is_locked && <Alert severity="warning">הקריאה נעולה לשינויים{item.lock_reason ? `: ${item.lock_reason}` : ''}. ניתן עדיין להגיב.</Alert>}
    <Grid container spacing={2.5} alignItems="flex-start"><Grid size={{ xs: 12, lg: 7 }}><Stack spacing={2.5}>
      <Card sx={{ borderRadius: 3 }}><CardContent><Typography variant="h6" fontWeight={800}>פרטי הקריאה</Typography><Divider sx={{ my: 2 }}/><Stack spacing={2}><InlineTextField label="תיאור" value={item.description || ''} multiline editable={editable} onSave={(description) => patch({ description })}/><Grid container spacing={2}><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption" color="text.secondary">סוג קריאה</Typography><Typography fontWeight={700}>{types.find((row) => row.id === item.request_type_id)?.name_he || '—'}</Typography></Grid><Grid size={{ xs: 12, sm: 6 }}><FormControl fullWidth><InputLabel>סטטוס</InputLabel><Select label="סטטוס" value={item.workflow_status_id || ''} onChange={(event) => transition(event.target.value)}>{statuses.map((status) => <Tooltip key={status.id} title={status.reason || ''} placement="left"><span><MenuItem value={status.id} disabled={!status.allowed && !status.current}>{status.label_he}{status.current ? ' · נוכחי' : ''}</MenuItem></span></Tooltip>)}</Select></FormControl></Grid><Grid size={{ xs: 12, sm: 6 }}><TextField select fullWidth label="עדיפות" value={item.priority_id || ''} disabled={!editable} onChange={(event) => patch({ priority_id: event.target.value })}>{priorities.filter((row) => row.is_active).map((row) => <MenuItem key={row.id} value={row.id}>{row.label_he}</MenuItem>)}</TextField></Grid><Grid size={{ xs: 12, sm: 6 }}><TextField select fullWidth label="תת-עדיפות" value={item.sub_priority_id || ''} disabled={!editable} onChange={(event) => patch({ sub_priority_id: event.target.value || null })}><MenuItem value="">ללא</MenuItem>{subs.filter((row) => row.is_active).map((row) => <MenuItem key={row.id} value={row.id}>{row.label_he}</MenuItem>)}</TextField></Grid></Grid></Stack></CardContent></Card>
      <Card sx={{ borderRadius: 3 }}><CardContent><Typography variant="h6" fontWeight={800}>משתתפים</Typography><Divider sx={{ my: 2 }}/><Stack direction="row" gap={1} flexWrap="wrap">{participants.length ? participants.map((row) => <Chip key={row.user_id} avatar={<Avatar>{row.display_name[0]}</Avatar>} label={row.display_name}/>) : <Typography color="text.secondary">אין משתתפים נוספים</Typography>}</Stack>{item.permissions.can_manage_participants && <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} mt={2}><TextField select fullWidth label="הוספת משתמש" value={participantId} onChange={(event) => setParticipantId(event.target.value)}>{candidates.map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</TextField><Button startIcon={<PersonAdd/>} disabled={!participantId} onClick={addParticipant}>הוספה</Button></Stack>}</CardContent></Card>
      <Card sx={{ borderRadius: 3 }}><CardContent><Typography variant="h6" fontWeight={800}>אישורים</Typography><Divider sx={{ my: 2 }}/><Typography color="text.secondary">אישורים פעילים מוצגים ומטופלים בהתאם לתהליך שהוגדר לסוג הקריאה.</Typography></CardContent></Card><CaseAttachments caseId={item.id}/>
    </Stack></Grid><Grid size={{ xs: 12, lg: 5 }} sx={{ position: { lg: 'sticky' }, top: 88 }}><Card sx={{ borderRadius: 3 }}><CardContent><Typography variant="h6" fontWeight={800}>שיחה</Typography><Divider sx={{ my: 2 }}/><Box sx={{ minHeight: 260, maxHeight: 520, overflowY: 'auto' }}><Feed rows={comments} me={me}/></Box><Divider sx={{ my: 2 }}/><TextField fullWidth multiline minRows={3} label="כתיבת תגובה" value={body} onChange={(event) => setBody(event.target.value)}/><Button fullWidth sx={{ mt: 1.5 }} variant="contained" endIcon={<Send/>} disabled={!body.trim() || send.isPending} onClick={() => send.mutate()}>שליחה</Button></CardContent></Card></Grid></Grid>
    <CaseLockDialog open={lockOpen} locked={item.is_locked} onClose={() => setLockOpen(false)} onSave={saveLock}/>
  </Stack></Container></Box>;
}
