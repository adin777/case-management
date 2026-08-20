import { Checkbox, FormControl, InputLabel, ListItemText, MenuItem, Select, type SelectChangeEvent } from '@mui/material';
import { useTranslation } from 'react-i18next';
import '../i18n';
import type { AppSelectOption } from './AppSelect';

export function AppMultiSelect({ label, value, options, onChange }:{label:string;value:string[];options:AppSelectOption[];onChange:(value:string[])=>void}) {
  const { t } = useTranslation();
  return <FormControl fullWidth><InputLabel>{label}</InputLabel><Select<string[]> multiple label={label} value={value} onChange={(event:SelectChangeEvent<string[]>)=>onChange(typeof event.target.value==='string'?event.target.value.split(','):event.target.value)} renderValue={selected=>selected.map((id:string)=>options.find(option=>option.value===id)?.label||id).join(', ')}>
    {options.length ? options.map(option=><MenuItem key={option.value} value={option.value}><Checkbox checked={value.includes(option.value)}/><ListItemText primary={option.label}/></MenuItem>) : <MenuItem disabled>{t('common.noOptions')}</MenuItem>}
  </Select></FormControl>;
}
