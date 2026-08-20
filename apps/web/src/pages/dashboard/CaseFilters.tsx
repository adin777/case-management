import { Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Tooltip } from '@mui/material';
import type { CaseField, Environment } from '../../types';
import type { WorkspaceFilters } from './types';
import {useTranslation} from 'react-i18next';
import {localized} from '../../i18n';

export function CaseFilters({ value, environments, fields, onChange }: { value: WorkspaceFilters; environments: Environment[]; fields: CaseField[]; onChange: (value: WorkspaceFilters) => void }) {
  const {t,i18n}=useTranslation();
  const set = (key: keyof WorkspaceFilters, next: string) => onChange({ ...value, [key]: next });
  return <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}><Stack direction={{ xs: 'column', md: 'row' }} gap={1.5} flexWrap="wrap">
    <TextField select size="small" label={t('dashboard.activity')} value={value.activity_state} onChange={(event) => set('activity_state', event.target.value)} sx={{ minWidth: 150 }}><MenuItem value="active">{t('dashboard.active')}</MenuItem><MenuItem value="inactive">{t('dashboard.inactive')}</MenuItem><MenuItem value="all">{t('dashboard.all')}</MenuItem></TextField>
    <TextField size="small" type="date" label={t('dashboard.createdFrom')} value={value.created_from} onChange={(event) => set('created_from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/><TextField size="small" type="date" label={t('dashboard.createdTo')} value={value.created_to} onChange={(event) => set('created_to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
    <TextField size="small" label={t('cases.subject')} value={value.title} onChange={(event) => set('title', event.target.value)}/><TextField size="small" type="date" label={t('dashboard.updatedFrom')} value={value.updated_from} onChange={(event) => set('updated_from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/><TextField size="small" type="date" label={t('dashboard.updatedTo')} value={value.updated_to} onChange={(event) => set('updated_to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
    <TextField select size="small" label={t('cases.environment')} value={value.environment_id} onChange={(event) => onChange({ ...value, environment_id: event.target.value, dynamic: {} })} sx={{ minWidth: 180 }}><MenuItem value="">{t('dashboard.allEnvironments')}</MenuItem>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{localized(environment.name_he,environment.name_en,i18n.language)}</MenuItem>)}</TextField>
    <Tooltip title={t('dashboard.participatingHelp')}><FormControlLabel control={<Checkbox checked={value.include_participating} onChange={(event) => onChange({ ...value, include_participating: event.target.checked })}/>} label={t('dashboard.participating')}/></Tooltip>
    {fields.map((field) => <TextField key={field.id} select={field.field_type.includes('select')} size="small" label={localized(field.label_he,field.label_en,i18n.language)} value={value.dynamic[field.id] || ''} onChange={(event) => onChange({ ...value, dynamic: { ...value.dynamic, [field.id]: event.target.value } })} sx={{ minWidth: 160 }}>{field.field_type.includes('select') && [<MenuItem key="none" value="">{t('dashboard.all')}</MenuItem>, ...field.options_json.filter((option) => option.is_active).map((option) => <MenuItem key={option.value} value={option.value}>{localized(option.label_he,option.label_en,i18n.language)}</MenuItem>)]}</TextField>)}
  </Stack></Paper>;
}
