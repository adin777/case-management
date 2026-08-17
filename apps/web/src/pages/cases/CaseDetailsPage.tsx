import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Close, Lock, LockOpen, PersonAdd } from '@mui/icons-material';
import { Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, Container, Divider, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Stack, TextField, Tooltip, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Case, Field, Participant, RequestType, User } from '../../types';
import { DynamicField } from '../../components/DynamicField';
import { statusLabel } from '../../status';
import { CaseAttachments } from './details/CaseAttachments';
import { CaseLockDialog } from './details/CaseLockDialog';
import { ConversationPanel } from './details/ConversationPanel';
import { CaseApprovalsPanel } from './details/CaseApprovalsPanel';
import { InlineTextField } from './details/InlineTextField';
import { CaseTransferWizard } from './details/CaseTransferWizard';

type StatusOption = { id: string; label_he: string; current: boolean; allowed: boolean; reason?: string };
type CaseWithEnvironment = Case & { environment_name?: string };

export function CaseDetailsPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [participantId, setParticipantId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [lockOpen, setLockOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [globalValues, setGlobalValues] = useState<Record<string,unknown>>({});
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: item, isLoading } = useQuery({ queryKey: ['case', id], queryFn: () => api<CaseWithEnvironment>(`/cases/${id}`) });
  const enabled = !!item;
  const { data: types = [] } = useQuery({ queryKey: ['request-types', item?.environment_id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${item!.environment_id}`), enabled });
  const { data: statuses = [] } = useQuery({ queryKey: ['status-options', id, item?.workflow_status_id], queryFn: () => api<StatusOption[]>(`/cases/${id}/status-options`), enabled });
  const { data: participants = [] } = useQuery({ queryKey: ['participants', id], queryFn: () => api<Participant[]>(`/cases/${id}/participants`), enabled });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: assignees = [] } = useQuery({ queryKey: ['eligible-assignees', item?.environment_id], queryFn: () => api<User[]>(`/environments/${item!.environment_id}/eligible-assignees`), enabled: enabled && !!item?.permissions.can_assign && !item?.is_locked });
  const { data: caseFields = {global_fields:[] as Field[],environment_fields:[] as Field[]} } = useQuery({ queryKey: ['case-fields', item?.environment_id, item?.request_type_id], queryFn: () => api<{global_fields:Field[];environment_fields:Field[]}>(`/environments/${item!.environment_id}/case-fields?request_type_id=${item!.request_type_id}&presentation=edit`), enabled });
  const hasBoundAssigneeField = caseFields.global_fields.some((field) => field.semantic_binding === 'case.assignee');
  const { data: storedGlobalValues = {} } = useQuery({ queryKey: ['case-global-field-values', id], queryFn: () => api<Record<string,unknown>>(`/cases/${id}/global-field-values`), enabled });
  useEffect(()=>setGlobalValues(storedGlobalValues),[storedGlobalValues]);
  const candidates = useMemo(() => users.filter((user) => user.is_active !== false && !participants.some((row) => row.user_id === user.id)), [users, participants]);
  const refresh = () => qc.invalidateQueries({ queryKey: ['case', id] });
  async function patch(payload: object) {
    try {
      await api(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify({ ...payload, version: item!.version }) });
      setSuccess('השינוי נשמר'); await refresh();
    } catch (caught) { setError((caught as Error).message); throw caught; }
  }
  async function transition(workflow_status_id: string) {
    try { await api(`/cases/${id}/transitions`, { method: 'POST', body: JSON.stringify({ workflow_status_id }) }); await refresh(); }
    catch (caught) { setError((caught as Error).message); }
  }
  async function assign(assignee_id: string) { try { await api(`/cases/${id}/assign`, { method: 'POST', body: JSON.stringify({ assignee_id: assignee_id || null, version: item!.version }) }); await refresh(); } catch (caught) { setError((caught as Error).message); } }
  async function addParticipant() {
    try {
      await api(`/cases/${id}/participants`, { method: 'POST', body: JSON.stringify({ user_id: participantId, participant_type: 'participant' }) });
      setParticipantId(''); qc.invalidateQueries({ queryKey: ['participants', id] });
    } catch (caught) { setError((caught as Error).message); }
  }
  async function removeParticipant(userId: string) {
    try { await api(`/cases/${id}/participants/${userId}`, { method: 'DELETE' }); qc.invalidateQueries({ queryKey: ['participants', id] }); }
    catch (caught) { setError((caught as Error).message); }
  }
  async function saveLock(reason: string) {
    await api(`/cases/${id}/lock`, { method: 'POST', body: JSON.stringify({ locked: !item!.is_locked, reason: reason || null, version: item!.version }) });
    setLockOpen(false); await refresh();
  }
  async function saveGlobalFields(){try{const saved=await api<Record<string,unknown>>(`/cases/${id}/global-field-values`,{method:'PUT',body:JSON.stringify(globalValues)});setGlobalValues(saved);setSuccess('השדות הגלובליים נשמרו ואומתו מחדש');await qc.invalidateQueries({queryKey:['case-global-field-values',id]});}catch(caught){setError((caught as Error).message);}}
  if (isLoading || !item) return <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 400 }}><CircularProgress/></Box>;
  const editable = item.permissions.can_edit;
  const currentStatus = statuses.find((row) => row.current)?.label_he || statusLabel(item.status);
  return <Box sx={{ minHeight: '100%', py: 3 }}><Container maxWidth="xl"><Stack spacing={2.5}>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
    {success && <Alert severity="success" onClose={() => setSuccess('')}>{success}</Alert>}
    <Paper className="case-hero" elevation={0}>
      <Stack direction="row" gap={2} alignItems="center"><Typography color="primary" fontWeight={850}>{item.case_number}</Typography><Typography variant="body2"><strong>סביבה:</strong> {item.environment_name||'לא זמינה'}</Typography></Stack>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
        <Box sx={{ flex: 1 }}><InlineTextField label="נושא" value={item.title} editable={editable} onSave={(title) => patch({ title })}/>
          <Stack direction={{ xs: 'column', sm: 'row' }} gap={{ xs: .5, sm: 2 }} mt={1} color="text.secondary"><Typography variant="body2"><strong>פותח הקריאה:</strong> {item.reporter_name || 'לא זמין'} · {item.reporter_email || 'לא זמין'}</Typography><Typography variant="body2"><strong>נפתחה:</strong> {new Date(item.created_at).toLocaleString('he-IL')}</Typography><Typography variant="body2"><strong>עודכנה לאחרונה:</strong> {item.updated_at ? new Date(item.updated_at).toLocaleString('he-IL') : 'לא זמין'}</Typography></Stack>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center"><Chip color="primary" label={currentStatus}/>
          {item.is_locked && <Chip color="warning" icon={<Lock/>} label="נעולה לשינויים"/>}
          {item.permissions.can_lock && <Button variant="outlined" color="warning" startIcon={item.is_locked ? <LockOpen/> : <Lock/>} onClick={() => setLockOpen(true)}>{item.is_locked ? 'פתיחת נעילה' : 'נעילת קריאה'}</Button>}
          {item.permissions.can_transfer && <Button variant="outlined" onClick={() => setTransferOpen(true)}>העברת קריאה לסביבה אחרת</Button>}
        </Stack>
      </Stack>
    </Paper>
    {item.is_locked && <Alert severity="warning">הקריאה נעולה לשינויים{item.lock_reason ? `: ${item.lock_reason}` : ''}. ניתן עדיין להגיב.</Alert>}
    <Grid container spacing={2.5} alignItems="flex-start">
      <Grid size={{ xs: 12, lg: 5 }} sx={{ position: { lg: 'sticky' }, top: 88 }}><ConversationPanel caseId={item.id} permissions={item.permissions} me={me} onError={setError}/></Grid>
      <Grid size={{ xs: 12, lg: 7 }}><Stack spacing={2.5}>
        <Card><CardContent><Typography variant="h6">פרטי הקריאה</Typography><Divider sx={{ my: 2 }}/><Stack spacing={2}>
          <InlineTextField label="תיאור" value={item.description || ''} multiline editable={editable} onSave={(description) => patch({ description })}/>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}><TextField select fullWidth label="סוג קריאה" value={item.request_type_id} disabled={!editable} onChange={(event) => patch({ request_type_id: event.target.value })}>{types.filter((row) => row.is_active).map((row) => <MenuItem key={row.id} value={row.id}>{row.name_he}</MenuItem>)}</TextField></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><FormControl fullWidth><InputLabel>סטטוס</InputLabel><Select label="סטטוס" value={item.workflow_status_id || ''} disabled={!item.permissions.can_change_status} onChange={(event) => transition(event.target.value)}>{statuses.map((status) => <Tooltip key={status.id} title={status.reason || ''} placement="left"><span><MenuItem value={status.id} disabled={!status.allowed && !status.current}>{status.label_he}{status.current ? ' · נוכחי' : ''}</MenuItem></span></Tooltip>)}</Select></FormControl></Grid>
            {!hasBoundAssigneeField && <Grid size={{ xs: 12, sm: 6 }}><TextField select fullWidth label="מטפל" value={item.assignee_id || ''} disabled={!item.permissions.can_assign || item.is_locked} onChange={(event) => assign(event.target.value)}><MenuItem value="">ללא מטפל</MenuItem>{assignees.map((row) => <MenuItem key={row.id} value={row.id}>{row.display_name} · {row.email}</MenuItem>)}</TextField></Grid>}
          </Grid>
        </Stack></CardContent></Card>
        {!!caseFields.global_fields.length&&<Card><CardContent><Typography variant="h6">שדות גלובליים</Typography><Divider sx={{my:2}}/><Stack spacing={2}>{caseFields.global_fields.map(field=><DynamicField key={field.id} field={field} value={field.id?globalValues[field.id]:undefined} users={field.semantic_binding==='case.assignee'?assignees:users} onChange={value=>field.id&&setGlobalValues(current=>({...current,[field.id!]:value}))}/>)}{editable&&<Button variant="contained" onClick={saveGlobalFields} sx={{alignSelf:'flex-start'}}>שמירת שדות</Button>}</Stack></CardContent></Card>}
        <Card><CardContent><Typography variant="h6">משתתפים</Typography><Divider sx={{ my: 2 }}/><Stack direction="row" gap={1} flexWrap="wrap">{participants.length ? participants.map((row) => <Chip key={row.user_id} avatar={<Avatar>{row.display_name[0]}</Avatar>} label={row.display_name} onDelete={item.permissions.can_manage_participants ? () => removeParticipant(row.user_id) : undefined} deleteIcon={item.permissions.can_manage_participants ? <Close/> : undefined}/>) : <Typography color="text.secondary">אין משתתפים נוספים</Typography>}</Stack>
          {item.permissions.can_manage_participants && <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} mt={2}><TextField select fullWidth label="הוספת משתמש" value={participantId} onChange={(event) => setParticipantId(event.target.value)}>{candidates.map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</TextField><Button startIcon={<PersonAdd/>} disabled={!participantId} onClick={addParticipant}>הוספה</Button></Stack>}
        </CardContent></Card>
        <CaseApprovalsPanel caseId={item.id}/>
        <CaseAttachments caseId={item.id}/>
      </Stack></Grid>
    </Grid>
    <CaseLockDialog open={lockOpen} locked={item.is_locked} onClose={() => setLockOpen(false)} onSave={saveLock}/>
    <CaseTransferWizard caseId={item.id} currentEnvironmentId={item.environment_id} open={transferOpen} onClose={()=>setTransferOpen(false)} onTransferred={()=>{setSuccess('הקריאה הועברה בהצלחה');refresh()}}/>
  </Stack></Container></Box>;
}
