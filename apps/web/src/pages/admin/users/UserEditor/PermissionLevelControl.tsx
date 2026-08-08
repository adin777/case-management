import { ToggleButton, ToggleButtonGroup } from '@mui/material';

export type UserAccessLevel = 'inherit' | 'none' | 'view' | 'edit';

export function PermissionLevelControl({ value, onChange, inherit = false }: { value: UserAccessLevel; onChange: (value: UserAccessLevel) => void; inherit?: boolean }) {
  return <ToggleButtonGroup exclusive size="small" value={value} onChange={(_, next) => next && onChange(next)} fullWidth>
    {inherit && <ToggleButton value="inherit">ירושה</ToggleButton>}
    <ToggleButton value="none">ללא</ToggleButton><ToggleButton value="view">צפייה</ToggleButton><ToggleButton value="edit">עריכה</ToggleButton>
  </ToggleButtonGroup>;
}
