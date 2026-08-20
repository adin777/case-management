import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, CardContent, CircularProgress, Container, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import { DynamicField } from '../../components/DynamicField';
import type { Case, Environment, Form, RequestType, User } from '../../types';
import { activeRequestTypes, caseCreationConfigurationUrl } from './caseCreationSources';
import { useTranslation } from 'react-i18next';
import { localized } from '../../i18n';
import { AppSelect } from '../../components/AppSelect';
import { AppMultiSelect } from '../../components/AppMultiSelect';

type CreationType=RequestType&{form?:Form};
type CreationConfig={request_types:CreationType[];global_fields:Form['fields'];participants:User[];eligible_assignees:User[]};

export function CreateCasePage() {
  const { t, i18n } = useTranslation();
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
  const requestTypeRows=creationConfig?.request_types||[];const globalFields=creationConfig?.global_fields||[];const users=creationConfig?.participants||[];const eligibleAssignees=creationConfig?.eligible_assignees||[];
  const requestTypes = activeRequestTypes(requestTypeRows, environmentId);
  const selectedType = requestTypes.find((item) => item.id === requestTypeId);
  const caseConfig=selectedType as CreationType|undefined;const form=caseConfig?.form;

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    const missing = [...globalFields,...(form?.fields||[])].filter((field) => field.is_active !== false && field.is_required && (values[field.id!] === undefined || values[field.id!] === ''));
    if (missing?.length) { setError(t('cases.fieldsRequired',{fields:missing.map((field) => localized(field.label_he,field.label_en,i18n.language)).join(', ')})); return; }
    if (!environmentId || !requestTypeId || !title.trim() || !description.trim()) { setError(t('cases.coreRequired')); return; }
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
    <div><Typography variant="h4" fontWeight={800}>{t('cases.createTitle')}</Typography><Typography color="text.secondary">{t('cases.createSubtitle')}</Typography></div>
    {error && <Alert severity="error">{error}</Alert>}
    {environmentsError && <Alert severity="error">{t('cases.loadEnvironmentsFailed')}</Alert>}
    <Card variant="outlined"><CardContent><Stack component="form" noValidate onSubmit={submit} spacing={2.5}>
      <AppSelect required label={t('cases.environment')} value={environmentId} onChange={(value) => { setEnvironmentId(value); setRequestTypeId(''); setValues({}); }} options={environments.map(environment=>({value:environment.id,label:localized(environment.name_he,environment.name_en,i18n.language)}))}/>
      <TextField label={t('cases.subject')} value={title} onChange={(event) => setTitle(event.target.value)} />
      <TextField label={t('cases.description')} multiline minRows={4} value={description} onChange={(event) => setDescription(event.target.value)} />
      <AppSelect required disabled={!environmentId} label={t('cases.requestType')} value={requestTypeId} onChange={setRequestTypeId} options={requestTypes.map(type=>({value:type.id,label:localized(type.name_he,type.name_en,i18n.language)}))}/>
      {configError && <Alert severity="error">{t('cases.loadConfigFailed')}</Alert>}
      <AppMultiSelect label={t('cases.participants')} value={participantIds} onChange={setParticipantIds} options={users.filter(user=>user.is_active!==false).map(user=>({value:user.id,label:`${user.display_name} · ${user.email}`}))}/>
      {[...globalFields,...(form?.fields||[])].filter((field) => field.is_active !== false).map((field) => <Stack key={field.id} spacing={1}><DynamicField field={{...field,label_he:localized(field.label_he,field.label_en,i18n.language)}} value={values[field.id!]} users={field.semantic_binding==='case.assignee'?eligibleAssignees:users} onChange={(value) => setValues({ ...values, [field.id!]: value })} />{field.semantic_binding==='case.assignee'&&!eligibleAssignees.length&&<Alert severity="info">{t('cases.noAssignees')}</Alert>}</Stack>)}
      <Button type="submit" variant="contained" size="large" disabled={!caseConfig || submitting}>{submitting ? <><CircularProgress size={20} color="inherit" sx={{ ml: 1 }} />{t('cases.submitting')}</> : t('cases.submit')}</Button>
    </Stack></CardContent></Card>
  </Stack></Container>;
}
