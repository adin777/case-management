import { ToggleButton, ToggleButtonGroup } from '@mui/material';
import { useTranslation } from 'react-i18next';

export type AccessLevel = 'inherit' | 'none' | 'view' | 'edit';
export function AccessLevelSelector({ value, onChange, allowInherit = false, disabled = false, inheritedLevel }: { value: AccessLevel; onChange: (value: AccessLevel) => void; allowInherit?: boolean; disabled?: boolean; inheritedLevel?:AccessLevel }) {
  const {t}=useTranslation();
  return <ToggleButtonGroup disabled={disabled} exclusive size="small" value={value} onChange={(_, next) => next && onChange(next)} fullWidth>{allowInherit&&<ToggleButton value="inherit">{inheritedLevel==='edit'?t('permissions.inheritEdit'):t('common.inherit')}</ToggleButton>}<ToggleButton value="none">{t('common.none')}</ToggleButton><ToggleButton value="view">{t('common.view')}</ToggleButton><ToggleButton value="edit">{t('common.edit')}</ToggleButton></ToggleButtonGroup>;
}
