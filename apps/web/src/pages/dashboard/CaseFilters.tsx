import { Search, Tune } from '@mui/icons-material';
import { Box, Button, Checkbox, FormControlLabel, InputAdornment, MenuItem, Paper, Stack, TextField, Tooltip, Typography } from '@mui/material';
import type { CaseField, Environment } from '../../types';
import type { WorkspaceFilters } from './types';
import { useTranslation } from 'react-i18next';
import { localized } from '../../i18n';

export function CaseFilters({ value, environments, fields, onChange, onReset }: { value: WorkspaceFilters; environments: Environment[]; fields: CaseField[]; onChange: (value: WorkspaceFilters) => void; onReset: () => void }) {
  const { t, i18n } = useTranslation();
  const set = (key: keyof WorkspaceFilters, next: string) => onChange({ ...value, [key]: next });
  return <Paper className="filter-panel" variant="outlined">
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1.5} mb={2}>
      <Stack direction="row" alignItems="center" gap={1}><Tune color="primary"/><Typography variant="h6">חיפוש ומסננים</Typography></Stack>
      <Button onClick={onReset}>ניקוי מסננים</Button>
    </Stack>
    <TextField fullWidth label="חיפוש חופשי" placeholder="מספר קריאה או נושא" value={value.search} onChange={(event) => set('search', event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search/></InputAdornment> } }} sx={{ mb: 2 }}/>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,minmax(0,1fr))', lg: 'repeat(4,minmax(0,1fr))' }, gap: 1.5 }}>
      <TextField select label={t('dashboard.activity')} value={value.activity_state} onChange={(event) => set('activity_state', event.target.value)}><MenuItem value="active">{t('dashboard.active')}</MenuItem><MenuItem value="inactive">{t('dashboard.inactive')}</MenuItem><MenuItem value="all">{t('dashboard.all')}</MenuItem></TextField>
      <TextField type="date" label={t('dashboard.createdFrom')} value={value.created_from} onChange={(event) => set('created_from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
      <TextField type="date" label={t('dashboard.createdTo')} value={value.created_to} onChange={(event) => set('created_to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
      <TextField label={t('cases.subject')} value={value.title} onChange={(event) => set('title', event.target.value)}/>
      <TextField type="date" label={t('dashboard.updatedFrom')} value={value.updated_from} onChange={(event) => set('updated_from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
      <TextField type="date" label={t('dashboard.updatedTo')} value={value.updated_to} onChange={(event) => set('updated_to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }}/>
      <TextField select label={t('cases.environment')} value={value.environment_id} onChange={(event) => onChange({ ...value, environment_id: event.target.value, dynamic: {} })}><MenuItem value="">{t('dashboard.allEnvironments')}</MenuItem>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{localized(environment.name_he, environment.name_en, i18n.language)}</MenuItem>)}</TextField>
      {fields.map((field) => <TextField key={field.id} select={field.field_type.includes('select')} label={localized(field.label_he, field.label_en, i18n.language)} value={value.dynamic[field.id] || ''} onChange={(event) => onChange({ ...value, dynamic: { ...value.dynamic, [field.id]: event.target.value } })}>{field.field_type.includes('select') && [<MenuItem key="none" value="">{t('dashboard.all')}</MenuItem>, ...field.options_json.filter((option) => option.is_active).map((option) => <MenuItem key={option.value} value={option.value}>{localized(option.label_he, option.label_en, i18n.language)}</MenuItem>)]}</TextField>)}
    </Box>
    <Tooltip title={t('dashboard.participatingHelp')}><FormControlLabel sx={{ mt: 1.5 }} control={<Checkbox checked={value.include_participating} onChange={(event) => onChange({ ...value, include_participating: event.target.checked })}/>} label={t('dashboard.participating')}/></Tooltip>
  </Paper>;
}
