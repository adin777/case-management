import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { DescriptionOutlined, InfoOutlined } from '@mui/icons-material';
import { Alert, Box, Card, CardContent, CircularProgress, Container, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import type { Case, Field, Participant, RequestType, User } from '../../types';
import { CaseAttachments } from './details/CaseAttachments';
import { CaseLockDialog } from './details/CaseLockDialog';
import { ConversationPanel } from './details/ConversationPanel';
import { CaseApprovalsPanel } from './details/CaseApprovalsPanel';
import { InlineTextField } from './details/InlineTextField';
import { CaseTransferWizard } from './details/CaseTransferWizard';
import { RelatedCasesPanel } from './details/RelatedCasesPanel';
import { CaseDetailsHeader } from './details/CaseDetailsHeader';
import { CaseSection } from './details/CaseSection';
import { GlobalFieldsPanel } from './details/GlobalFieldsPanel';
import { ParticipantsPanel } from './details/ParticipantsPanel';

type CaseWithEnvironment = Case & { environment_name?: string };
type CaseFields = { global_fields: Field[]; environment_fields: Field[] };

export function CaseDetailsPage() {
  const { id } = useParams(); const qc = useQueryClient(); const detailsRef = useRef<HTMLDivElement>(null);
  const [participantId, setParticipantId] = useState(''); const [error, setError] = useState(''); const [success, setSuccess] = useState('');
  const [lockOpen, setLockOpen] = useState(false); const [transferOpen, setTransferOpen] = useState(false); const [savingFields, setSavingFields] = useState(false);
  const [globalValues, setGlobalValues] = useState<Record<string, unknown>>({});
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const { data: item, isLoading } = useQuery({ queryKey: ['case', id], queryFn: () => api<CaseWithEnvironment>(`/cases/${id}`) });
  const enabled = Boolean(item);
  const { data: types = [] } = useQuery({ queryKey: ['request-types', item?.environment_id], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${item!.environment_id}`), enabled });
  const { data: participants = [] } = useQuery({ queryKey: ['participants', id], queryFn: () => api<Participant[]>(`/cases/${id}/participants`), enabled });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users'), retry: false });
  const { data: assignees = [] } = useQuery({ queryKey: ['eligible-assignees', item?.environment_id], queryFn: () => api<User[]>(`/environments/${item!.environment_id}/eligible-assignees`), enabled: enabled && Boolean(item?.permissions.can_assign) });
  const { data: caseFields = { global_fields: [], environment_fields: [] } } = useQuery({ queryKey: ['case-fields', item?.environment_id, item?.request_type_id], queryFn: () => api<CaseFields>(`/environments/${item!.environment_id}/case-fields?request_type_id=${item!.request_type_id}&presentation=edit`), enabled });
  const { data: storedGlobalValues = {} } = useQuery({ queryKey: ['case-global-field-values', id], queryFn: () => api<Record<string, unknown>>(`/cases/${id}/global-field-values`), enabled });
  useEffect(() => setGlobalValues(storedGlobalValues), [storedGlobalValues]);
  const candidates = useMemo(() => users.filter((user) => user.is_active !== false && !participants.some((row) => row.user_id === user.id)), [users, participants]);
  const refresh = () => qc.invalidateQueries({ queryKey: ['case', id] });
  const editable = Boolean(item?.permissions.can_edit);

  async function patch(payload: object) { try { await api(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify({ ...payload, version: item!.version }) }); setSuccess('השינוי נשמר'); await refresh(); } catch (caught) { setError((caught as Error).message); throw caught; } }
  async function addParticipant() { try { await api(`/cases/${id}/participants`, { method: 'POST', body: JSON.stringify({ user_id: participantId, participant_type: 'participant' }) }); setParticipantId(''); await qc.invalidateQueries({ queryKey: ['participants', id] }); } catch (caught) { setError((caught as Error).message); } }
  async function removeParticipant(userId: string) { try { await api(`/cases/${id}/participants/${userId}`, { method: 'DELETE' }); await qc.invalidateQueries({ queryKey: ['participants', id] }); } catch (caught) { setError((caught as Error).message); } }
  async function saveLock(reason: string) { await api(`/cases/${id}/lock`, { method: 'POST', body: JSON.stringify({ locked: !item!.is_locked, reason: reason || null, version: item!.version }) }); setLockOpen(false); await refresh(); }
  async function saveGlobalFields() { setSavingFields(true); try { const saved = await api<Record<string, unknown>>(`/cases/${id}/global-field-values`, { method: 'PUT', body: JSON.stringify(globalValues) }); setGlobalValues(saved); setSuccess('השדות הגלובליים נשמרו'); await Promise.all([qc.invalidateQueries({ queryKey: ['case-global-field-values', id] }), refresh()]); } catch (caught) { setError((caught as Error).message); } finally { setSavingFields(false); } }
  if (isLoading || !item) return <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 480 }}><CircularProgress/></Box>;

  return <Box className="case-details-page"><Container maxWidth="xl"><Stack spacing={2.5}>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}{success && <Alert severity="success" onClose={() => setSuccess('')}>{success}</Alert>}
    <CaseDetailsHeader item={item} status={item.status_label || 'ללא סטטוס'} onEdit={() => detailsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })} onLock={() => setLockOpen(true)} onTransfer={() => setTransferOpen(true)}/>
    {item.is_locked && <Alert severity="warning" variant="filled">הקריאה נעולה לשינויים{item.lock_reason ? `: ${item.lock_reason}` : ''}. משתמש רגיל יכול להמשיך להגיב בלבד.</Alert>}
    <Grid container spacing={2.5} alignItems="flex-start">
      <Grid size={{ xs: 12, lg: 8 }}><Stack spacing={2.5}>
        <Box ref={detailsRef}><CaseSection title="פרטי הקריאה" icon={<DescriptionOutlined/>}><Stack spacing={2.25}>
          <InlineTextField label="נושא" value={item.title} editable={editable} onSave={(title) => patch({ title })}/>
          <InlineTextField label="תיאור" value={item.description || ''} multiline editable={editable} onSave={(description) => patch({ description })}/>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
            <TextField select fullWidth label="סוג קריאה" value={item.request_type_id} disabled={!editable} onChange={(event) => patch({ request_type_id: event.target.value })}>{types.filter((row) => row.is_active).map((row) => <MenuItem key={row.id} value={row.id}>{row.localized_name || row.name_he}</MenuItem>)}</TextField>
            <Card variant="outlined" sx={{ p: 1.5, bgcolor: '#f8fafc', boxShadow: 'none' }}><CardContent sx={{ p: '0!important' }}><Typography variant="caption" color="text.secondary">פותח הקריאה</Typography><Typography fontWeight={750}>{item.reporter_name || 'לא זמין'}</Typography><Typography variant="body2" color="text.secondary">{item.reporter_email || ''}</Typography></CardContent></Card>
            <Card variant="outlined" sx={{ p: 1.5, bgcolor: '#f8fafc', boxShadow: 'none' }}><CardContent sx={{ p: '0!important' }}><Typography variant="caption" color="text.secondary">סביבה</Typography><Typography fontWeight={750}>{item.environment_name || 'לא זמינה'}</Typography></CardContent></Card>
          </Box>
        </Stack></CaseSection></Box>
        <GlobalFieldsPanel fields={caseFields.global_fields} values={globalValues} users={users} assignees={assignees} editable={editable} saving={savingFields} onChange={(fieldId, value) => setGlobalValues((current) => ({ ...current, [fieldId]: value }))} onSave={saveGlobalFields}/>
        <ParticipantsPanel participants={participants} candidates={candidates} selected={participantId} canManage={item.permissions.can_manage_participants} onSelected={setParticipantId} onAdd={addParticipant} onRemove={removeParticipant}/>
        <CaseApprovalsPanel caseId={item.id}/>
      </Stack></Grid>
      <Grid size={{ xs: 12, lg: 4 }}><Stack spacing={2.5} sx={{ position: { lg: 'sticky' }, top: 88 }}>
        <ConversationPanel caseId={item.id} permissions={item.permissions} me={me} onError={setError}/><RelatedCasesPanel caseId={item.id} canEdit={editable}/><CaseAttachments caseId={item.id}/>
        <Alert icon={<InfoOutlined/>} severity="info">כל שינוי נשמר ומתווסף ליומן הביקורת של הקריאה.</Alert>
      </Stack></Grid>
    </Grid>
    <CaseLockDialog open={lockOpen} locked={item.is_locked} onClose={() => setLockOpen(false)} onSave={saveLock}/>
    <CaseTransferWizard caseId={item.id} currentEnvironmentId={item.environment_id} open={transferOpen} onClose={() => setTransferOpen(false)} onTransferred={() => { setSuccess('הקריאה הועברה בהצלחה'); void refresh(); }}/>
  </Stack></Container></Box>;
}
