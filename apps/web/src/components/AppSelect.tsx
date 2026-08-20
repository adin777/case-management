import { FormControl, InputLabel, MenuItem, Select, type SelectChangeEvent } from '@mui/material';
import { useTranslation } from 'react-i18next';
import '../i18n';

export type AppSelectOption = { value: string; label: string; disabled?: boolean };

export function AppSelect({ label, value, options, onChange, disabled = false, required = false, emptyOption }:
  { label:string; value:string; options:AppSelectOption[]; onChange:(value:string)=>void; disabled?:boolean; required?:boolean; emptyOption?:string }) {
  const { t } = useTranslation();
  return <FormControl fullWidth disabled={disabled} required={required}><InputLabel>{label}</InputLabel><Select label={label} value={value} onChange={(event:SelectChangeEvent) => onChange(event.target.value)} MenuProps={{ disableAutoFocusItem:false }}>
    {emptyOption !== undefined && <MenuItem value="">{emptyOption}</MenuItem>}
    {options.length ? options.map(option => <MenuItem key={option.value} value={option.value} disabled={option.disabled}>{option.label}</MenuItem>) : <MenuItem disabled>{t('common.noOptions')}</MenuItem>}
  </Select></FormControl>;
}
