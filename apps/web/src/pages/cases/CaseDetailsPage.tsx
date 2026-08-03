import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Edit, Lock, LockOpen, PersonAdd, Send } from '@mui/icons-material';
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, Container,
  Divider, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Stack, Tab, Tabs,
  TextField, Typography,
} from '@mui/material';
import { api } from '../../api/client';
import type { Case, Comment, Environment, Form, Participant, Priority, RequestType, User } from '../../types';
import { statusLabel } from '../../status';
import { CaseEditDialog } from './details/CaseEditDialog';
import { CaseLockDialog } from './details/CaseLockDialog';
type ApprovalView={id:string;system_number:string;name:string;status:string;current_step_order:number;tasks:{id:string;approver_user_id:string;status:string;decision?:string;comment?:string}[]};

function displayValue(value: Case['values'][number] | undefined) {
  if (!value) return '—';
  const resolved = value.value_text ?? value.value_number ?? value.value_boolean ?? value.value_date ?? value.value_datetime ?? value.value_user_id ?? value.value_json;
  if (typeof resolved === 'boolean') return resolved ? 'כן' : 'לא';
  if (Array.isArray(resolved)) return resolved.join(', ');
  if (resolved && typeof resolved === 'object') return Object.values(resolved as Record<string, unknown>).join(', ');
  return String(resolved ?? '—');
}

function ConversationFeed({ comments, currentUser, empty }: { comments: Comment[]; currentUser?: User; empty: string }) {
  if (!comments.length) return <Box sx={{ py: 7, textAlign: 'center', color: 'text.secondary' }}><Typography>{empty}</Typography><Typography variant="body2">ההודעה הראשונה תופיע כאן</Typography></Box>;
  return <Stack spacing={1.5}>{comments.map((comment) => {
    const mine = comment.author_id === currentUser?.id;
    return <Box key={comment.id} sx={{ display: 'flex', gap: 1, flexDirection: mine ? 'row-reverse' : 'row' }}>
      <Avatar sx={{ width: 34, height: 34 }}>{comment.author_name?.[0] || 'מ'}</Avatar>
      <Paper variant="outlined" sx={{ p: 1.5, maxWidth: '82%', bgcolor: mine ? 'primary.50' : 'background.paper' }}>
        <Typography variant="caption" fontWeight={700}>{comment.author_name || 'משתמש'}</Typography>
        <Typography sx={{ whiteSpace: 'pre-wrap' }}>{comment.body}</Typography>
        <Typography variant="caption" color="text.secondary">{new Date(comment.created_at).toLocaleString('he-IL')}</Typography>
      </Paper>
    </Box>;
  })}</Stack>;
}

export function CaseDetailsPage() {
  const { id } = useParams();
  const client = useQueryClient();
  const [conversationTab, setConversationTab] = useState(0);
  const [body, setBody] = useState('');
  const [participantId, setParticipantId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editOpen, setEditOpen] = useState(false);
  const [lockOpen, setLockOpen] = useState(false);
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: item, isLoading } = useQuery({ queryKey: ['case', id], queryFn: () => api<Case>(`/cases/${id}`) });
  const { data: form } = useQuery({ queryKey: ['form', item?.form_definition_id], queryFn: () => api<Form>(`/forms/${item!.form_definition_id}`), enabled: !!item });
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: requestTypes = [] } = useQuery({ queryKey: ['request-types', item?.environment_id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${item!.environment_id}`), enabled: !!item });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: priorities = [] } = useQuery({ queryKey: ['priorities', item?.environment_id], queryFn: () => api<Priority[]>(`/environments/${item!.environment_id}/priorities`), enabled: !!item });
  const { data: participants = [] } = useQuery({ queryKey: ['participants', id], queryFn: () => api<Participant[]>(`/cases/${id}/participants`), enabled: !!item });
  const { data: publicComments = [] } = useQuery({ queryKey: ['public-comments', id], queryFn: () => api<Comment[]>(`/cases/${id}/public-comments`), enabled: !!item });
  const { data: managerComments = [] } = useQuery({ queryKey: ['manager-comments', id], queryFn: () => api<Comment[]>(`/cases/${id}/manager-comments`), enabled: !!item?.permissions.can_read_manager_comments, retry: false });
  const { data: allowed = [] } = useQuery({ queryKey: ['transitions', id, item?.status], queryFn: () => api<string[]>(`/cases/${id}/allowed-transitions`), enabled: !!item?.permissions.can_change_status });
  const { data: approvals = [] } = useQuery({ queryKey: ['approvals', id], queryFn: () => api<ApprovalView[]>(`/cases/${id}/approvals`), enabled: !!item });
  const environment = environments.find((row) => row.id === item?.environment_id);
  const requestType = requestTypes.find((row) => row.id === item?.request_type_id);
  const reporter = users.find((row) => row.id === item?.reporter_id);
  const assignee = users.find((row) => row.id === item?.assignee_id);
  const refreshCase = () => client.invalidateQueries({ queryKey: ['case', id] });
  const comments = conversationTab === 0 ? publicComments : managerComments;

  const sendComment = useMutation({
    mutationFn: () => api(`/cases/${id}/${conversationTab === 0 ? 'public-comments' : 'manager-comments'}`, { method: 'POST', body: JSON.stringify({ body }) }),
    onSuccess: () => { setBody(''); setSuccess('ההודעה נשלחה'); client.invalidateQueries({ queryKey: [conversationTab === 0 ? 'public-comments' : 'manager-comments', id] }); },
    onError: (caught) => setError((caught as Error).message),
  });
  const participantCandidates = useMemo(() => users.filter((user) => !participants.some((participant) => participant.user_id === user.id)), [users, participants]);
  async function addParticipant() {
    await api(`/cases/${id}/participants`, { method: 'POST', body: JSON.stringify({ user_id: participantId, participant_type: 'participant' }) });
    setParticipantId(''); setSuccess('המשתתף נוסף'); client.invalidateQueries({ queryKey: ['participants', id] });
  }
  async function removeParticipant(userId: string) {
    if (!confirm('להסיר את המשתתף מהקריאה?')) return;
    await api(`/cases/${id}/participants/${userId}`, { method: 'DELETE' });
    client.invalidateQueries({ queryKey: ['participants', id] });
  }
  async function transition(status: string) {
    try { await api(`/cases/${id}/transitions`, { method: 'POST', body: JSON.stringify({ status }) }); refreshCase(); }
    catch (caught) { setError((caught as Error).message); }
  }
  async function assign(assignee_id: string) {
    try { await api(`/cases/${id}/assign`, { method: 'POST', body: JSON.stringify({ assignee_id: assignee_id || null, version: item!.version }) }); refreshCase(); }
    catch (caught) { setError((caught as Error).message); }
  }
  async function decide(taskId:string,decision:string){await api(`/approval-tasks/${taskId}/decision`,{method:'POST',body:JSON.stringify({decision})});client.invalidateQueries({queryKey:['approvals',id]})}
  async function saveCase(payload: object) { try { await api(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }); setEditOpen(false); setSuccess('פרטי הקריאה עודכנו'); await refreshCase(); } catch (caught) { setError((caught as Error).message); } }
  async function saveLock(reason: string) { try { await api(`/cases/${id}/lock`, { method: 'POST', body: JSON.stringify({ locked: !item!.is_locked, reason: reason || null, version: item!.version }) }); setLockOpen(false); setSuccess(item!.is_locked ? 'נעילת הקריאה נפתחה' : 'הקריאה ננעלה לשינויים'); await refreshCase(); } catch (caught) { setError((caught as Error).message); } }

  if (isLoading || !item) return <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 400 }}><CircularProgress /></Box>;
  return <Container maxWidth="xl"><Stack spacing={2}>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
    {success && <Alert severity="success" onClose={() => setSuccess('')}>{success}</Alert>}
    <Box><Typography color="primary" fontWeight={800}>{item.case_number}</Typography><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}><Typography variant="h4" fontWeight={800}>{item.title}</Typography><Stack direction="row" gap={1} flexWrap="wrap"><Chip label={statusLabel(item.status)} color="primary"/>{item.is_locked && <Chip icon={<Lock/>} color="warning" label="נעולה לשינויים"/>}{item.permissions.can_edit && <Button startIcon={<Edit/>} variant="outlined" onClick={() => setEditOpen(true)}>עריכת קריאה</Button>}{item.permissions.can_lock && <Button startIcon={item.is_locked ? <LockOpen/> : <Lock/>} color="warning" variant="outlined" onClick={() => setLockOpen(true)}>{item.is_locked ? 'פתיחת נעילה' : 'נעילת קריאה'}</Button>}</Stack></Stack>{item.is_locked && <Alert severity="warning" sx={{ mt: 1 }}>הקריאה נעולה לשינויים{item.lock_reason ? `: ${item.lock_reason}` : ''}. ניתן עדיין להוסיף תגובות.</Alert>}</Box>
    <Grid container spacing={3} alignItems="flex-start">
      <Grid size={{ xs: 12, md: 7 }}><Stack spacing={2}>
        <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>פרטי הקריאה</Typography><Divider sx={{ my: 1.5 }} /><Typography variant="caption" color="text.secondary">תיאור</Typography><Typography sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>{item.description}</Typography><Grid container spacing={2}><Grid size={{ xs: 6 }}><Typography variant="caption">סביבה</Typography><Typography fontWeight={600}>{environment?.name_he || '—'}</Typography></Grid><Grid size={{ xs: 6 }}><Typography variant="caption">סוג קריאה</Typography><Typography fontWeight={600}>{requestType?.name_he || '—'}</Typography></Grid><Grid size={{ xs: 6 }}><Typography variant="caption">פותח</Typography><Typography>{reporter?.display_name || '—'}</Typography></Grid><Grid size={{ xs: 6 }}><Typography variant="caption">תאריך פתיחה</Typography><Typography>{new Date(item.created_at).toLocaleString('he-IL')}</Typography></Grid>{form?.fields.map((field) => <Grid key={field.id} size={{ xs: 12, sm: 6 }}><Typography variant="caption">{field.label_he}</Typography><Typography>{displayValue(item.values.find((value) => value.field_definition_id === field.id))}</Typography></Grid>)}</Grid></CardContent></Card>
        <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>סיווג וטיפול</Typography><Divider sx={{ my: 1.5 }} /><Grid container spacing={2}><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">עדיפות</Typography><Typography>{item.priority}</Typography></Grid><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">מטפל</Typography><Typography>{assignee?.display_name || 'טרם הוקצה'}</Typography></Grid>{item.permissions.can_change_status && <Grid size={{ xs: 12, sm: 6 }}><FormControl fullWidth disabled={!allowed.length}><InputLabel>שינוי סטטוס</InputLabel><Select label="שינוי סטטוס" value="" onChange={(event) => transition(event.target.value)}>{allowed.map((status) => <MenuItem key={status} value={status}>{statusLabel(status)}</MenuItem>)}</Select></FormControl></Grid>}{item.permissions.can_assign && <Grid size={{ xs: 12, sm: 6 }}><FormControl fullWidth><InputLabel>הקצאת מטפל</InputLabel><Select label="הקצאת מטפל" value={item.assignee_id || ''} onChange={(event) => assign(event.target.value)}><MenuItem value="">ללא מטפל</MenuItem>{users.map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name}</MenuItem>)}</Select></FormControl></Grid>}</Grid></CardContent></Card>
        <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>משתתפים</Typography><Divider sx={{ my: 1.5 }} /><Stack direction="row" flexWrap="wrap" gap={1}>{participants.length ? participants.map((participant) => <Chip key={participant.user_id} avatar={<Avatar>{participant.display_name[0]}</Avatar>} label={participant.display_name} onDelete={item.permissions.can_manage_participants ? () => removeParticipant(participant.user_id) : undefined} />) : <Typography color="text.secondary">אין משתתפים נוספים בקריאה</Typography>}</Stack>{item.permissions.can_manage_participants && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}><TextField select fullWidth label="חיפוש והוספת משתמש" value={participantId} onChange={(event) => setParticipantId(event.target.value)}>{participantCandidates.map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</TextField><Button variant="outlined" startIcon={<PersonAdd />} disabled={!participantId} onClick={addParticipant}>הוספה</Button></Stack>}</CardContent></Card>
        <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>אישורים</Typography><Divider sx={{ my: 1.5 }}/>{approvals.length?approvals.map(flow=><Paper key={flow.id} variant="outlined" sx={{p:1.5,mb:1}}><Typography fontWeight={700}>{flow.name} · {flow.system_number}</Typography><Typography variant="body2">מצב: {flow.status} · שלב {flow.current_step_order}</Typography>{flow.tasks.map(task=><Stack key={task.id} direction={{xs:'column',sm:'row'}} gap={1} alignItems="center"><Typography variant="body2">{users.find(u=>u.id===task.approver_user_id)?.display_name||'מאשר'} · {task.status}</Typography>{task.approver_user_id===me?.id&&task.status==='pending'&&<><Button size="small" onClick={()=>decide(task.id,'approved')}>אישור</Button><Button size="small" color="error" onClick={()=>decide(task.id,'rejected')}>דחייה</Button><Button size="small" onClick={()=>decide(task.id,'returned')}>החזרה</Button></>}</Stack>)}</Paper>):<Typography color="text.secondary">אין סבב אישורים פעיל</Typography>}</CardContent></Card>
      </Stack></Grid>
      <Grid size={{ xs: 12, md: 5 }} sx={{ position: { md: 'sticky' }, top: { md: 88 } }}><Card variant="outlined"><Tabs value={conversationTab} onChange={(_, value) => setConversationTab(value)} variant="fullWidth"><Tab label="שיחה ציבורית" />{item.permissions.can_read_manager_comments && <Tab label="הודעות מנהלים" />}</Tabs><Divider /><Box sx={{ p: 2, height: { md: 'calc(100vh - 390px)' }, minHeight: 320, overflowY: 'auto' }}><ConversationFeed comments={comments} currentUser={me} empty={conversationTab === 0 ? 'עדיין אין הודעות בשיחה הציבורית' : 'עדיין אין הודעות מנהלים'} /></Box><Divider /><Stack spacing={1.5} sx={{ p: 2 }}><TextField multiline minRows={3} label={conversationTab === 0 ? 'כתיבת תגובה ציבורית' : 'כתיבת הודעת מנהלים'} value={body} onChange={(event) => setBody(event.target.value)} /><Button variant="contained" endIcon={sendComment.isPending ? <CircularProgress size={18} color="inherit" /> : <Send />} disabled={!body.trim() || sendComment.isPending || (conversationTab === 1 && !item.permissions.can_create_manager_comments)} onClick={() => sendComment.mutate()}>שליחה</Button></Stack></Card></Grid>
    </Grid>
    <CaseEditDialog open={editOpen} item={item} form={form} priorities={priorities} users={users} onClose={() => setEditOpen(false)} onSave={saveCase}/><CaseLockDialog open={lockOpen} locked={item.is_locked} onClose={() => setLockOpen(false)} onSave={saveLock}/>
  </Stack></Container>;
}
