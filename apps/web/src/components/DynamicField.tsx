import {Checkbox,FormControlLabel,TextField} from '@mui/material';
import {useTranslation} from 'react-i18next';
import type {Field,User} from '../types';
import {localized} from '../i18n';
import {AppMultiSelect} from './AppMultiSelect';
import {AppSelect,type AppSelectOption} from './AppSelect';

export function DynamicField({field,value,onChange,users=[]}:{field:Field;value:unknown;onChange:(value:unknown)=>void;users?:User[]}) {
  const {i18n}=useTranslation();const label=`${field.label || localized(field.label_he,field.label_en,i18n.language)}${field.is_required?' *':''}`;
  if(field.field_type==='boolean') return <FormControlLabel control={<Checkbox checked={Boolean(value)} onChange={event=>onChange(event.target.checked)}/>} label={label}/>;
  const options:AppSelectOption[]=field.field_type==='user'?users.map(user=>({value:user.id,label:user.display_name})):(field.configuration_json.options||[]).filter(option=>typeof option==='string'||option.is_active!==false).map(option=>typeof option==='string'?{value:option,label:option}:{value:option.id,label:option.label || localized(option.label_he,option.label_en,i18n.language)});
  if(field.field_type==='multi_select')return <AppMultiSelect label={label} value={(value as string[])||[]} options={options} onChange={onChange}/>;
  if(['single_select','user'].includes(field.field_type))return <AppSelect label={label} value={String(value||'')} options={options} onChange={onChange}/>;
  const type={number:'number',date:'date',datetime:'datetime-local'}[field.field_type]||'text';
  return <TextField label={label} type={type} multiline={['long_text','textarea'].includes(field.field_type)} minRows={['long_text','textarea'].includes(field.field_type)?3:undefined} value={value??''} onChange={event=>onChange(field.field_type==='number'?Number(event.target.value):event.target.value)} slotProps={type==='date'||type==='datetime-local'?{inputLabel:{shrink:true}}:undefined}/>;
}
