import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, CardContent, Chip, CircularProgress, Container, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import { DynamicField } from '../../components/DynamicField';
import type { Case, Environment, Form, RequestType, User } from '../../types';
import { activeRequestTypes, caseCreationConfigurationUrl } from './caseCreationSources';

type CreationType=RequestType&{form?:Form};
type CreationConfig={request_types:CreationType[];global_fields:Form['fields'];participants:User[]};

export function CreateCasePage() {
  const navigate = useNavigate();
  const [environmentId, setEnvironmentId] = useState('');
  const [requestTypeId, setRequestTypeId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { data: environments = [], error: environmentsError } = useQuery({ queryKey: ['case-creation-environments'], queryFn: () => api<Environment[]>('/case-creation/environments') });
  const { data: creationConfig, error: configError } = useQuery({ queryKey: ['case-creation-configuration', environmentId], queryFn: () => api<CreationConfig>(caseCreationConfigurationUrl(environmentId)), enabled: !!environmentId, retry:false });
  const requestTypeRows=creationConfig?.request_types||[];const globalFields=creationConfig?.global_fields||[];const users=creationConfig?.participants||[];
  const requestTypes = activeRequestTypes(requestTypeRows, environmentId);
  const selectedType = requestTypes.find((item) => item.id === requestTypeId);
  const caseConfig=selectedType as CreationType|undefined;const form=caseConfig?.form;

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    const missing = [...globalFields,...(form?.fields||[])].filter((field) => field.is_active !== false && field.is_required && (values[field.id!] === undefined || values[field.id!] === ''));
    if (missing?.length) { setError(`יש למלא: ${missing.map((field) => field.label_he).join(', ')}`); return; }
    if (!environmentId || !requestTypeId || !title.trim() || !description.trim()) { setError('יש למלא את כל שדות הליבה'); return; }
    setSubmitting(true);
    try {
      const result = await api<Case>('/cases', { method: 'POST', body: JSON.stringify({
        environment_id: environmentId, request_type_id: requestTypeId, title, description,
        participant_ids: participantIds,
        values: Object.entries(values).map(([field_definition_id, value]) => ({ field_definition_id, value })),
      }) });
      navigate(`/cases/${result.id}`);
    } catch (caught) { setError((caught as Error).message); }
    finally { setSubmitting(false); }
  }

  return <Container maxWidth="md"><Stack spacing={3}>
    <div><Typography variant="h4" fontWeight={800}>פתיחת קריאה חדשה</Typography><Typography color="text.secondary">מלאו את פרטי הליבה והוסיפו משתתפים לפי הצורך</Typography></div>
    {error && <Alert severity="error">{error}</Alert>}
    {environmentsError && <Alert severity="error">לא ניתן לטעון את הסביבות המורשות. {(environmentsError as Error).message}</Alert>}
    <Card variant="outlined"><CardContent><Stack component="form" onSubmit={submit} spacing={2.5}>
      <FormControl required><InputLabel>סביבה</InputLabel><Select label="סביבה" value={environmentId} onChange={(event) => { setEnvironmentId(event.target.value); setRequestTypeId(''); setValues({}); }}>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</Select></FormControl>
      <TextField label="נושא" required value={title} onChange={(event) => setTitle(event.target.value)} />
      <TextField label="תיאור" required multiline minRows={4} value={description} onChange={(event) => setDescription(event.target.value)} />
      <FormControl required disabled={!environmentId}><InputLabel>סוג קריאה</InputLabel><Select label="סוג קריאה" value={requestTypeId} onChange={(event) => setRequestTypeId(event.target.value)}>{requestTypes.map((type) => <MenuItem key={type.id} value={type.id}>{type.name_he}</MenuItem>)}</Select></FormControl>
      {configError && <Alert severity="error">לא ניתן לטעון את תצורת השדות. {(configError as Error).message}</Alert>}
      <FormControl><InputLabel>משתתפים</InputLabel><Select multiple label="משתתפים" value={participantIds} onChange={(event) => setParticipantIds(typeof event.target.value === 'string' ? event.target.value.split(',') : event.target.value)} renderValue={(selected) => <Stack direction="row" gap={.5} flexWrap="wrap">{selected.map((id) => <Chip key={id} size="small" label={users.find((user) => user.id === id)?.display_name || id} />)}</Stack>}>{users.filter((user) => user.is_active !== false).map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</Select></FormControl>
      {[...globalFields,...(form?.fields||[])].filter((field) => field.is_active !== false).map((field) => <DynamicField key={field.id} field={field} value={values[field.id!]} users={users} onChange={(value) => setValues({ ...values, [field.id!]: value })} />)}
      <Button type="submit" variant="contained" size="large" disabled={!caseConfig || submitting || !environmentId || !requestTypeId || !title.trim() || !description.trim()}>{submitting ? <><CircularProgress size={20} color="inherit" sx={{ ml: 1 }} />שומר קריאה...</> : 'פתיחת הקריאה'}</Button>
    </Stack></CardContent></Card>
  </Stack></Container>;
}
