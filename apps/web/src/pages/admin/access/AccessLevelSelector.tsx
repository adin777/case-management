import { ToggleButton, ToggleButtonGroup } from '@mui/material';

export type AccessLevel = 'none' | 'view' | 'edit';
export function AccessLevelSelector({ value, onChange }: { value: AccessLevel; onChange: (value: AccessLevel) => void }) {
  return <ToggleButtonGroup exclusive size="small" value={value} onChange={(_, next) => next && onChange(next)} fullWidth><ToggleButton value="none">ללא</ToggleButton><ToggleButton value="view">צפייה</ToggleButton><ToggleButton value="edit">עריכה</ToggleButton></ToggleButtonGroup>;
}
