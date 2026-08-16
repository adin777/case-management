import { ToggleButton, ToggleButtonGroup } from '@mui/material';

export type AccessLevel = 'inherit' | 'none' | 'view' | 'edit';
export function AccessLevelSelector({ value, onChange, allowInherit = false, disabled = false }: { value: AccessLevel; onChange: (value: AccessLevel) => void; allowInherit?: boolean; disabled?: boolean }) {
  return <ToggleButtonGroup disabled={disabled} exclusive size="small" value={value} onChange={(_, next) => next && onChange(next)} fullWidth>{allowInherit&&<ToggleButton value="inherit">ירושה</ToggleButton>}<ToggleButton value="none">ללא</ToggleButton><ToggleButton value="view">צפייה</ToggleButton><ToggleButton value="edit">עריכה</ToggleButton></ToggleButtonGroup>;
}
