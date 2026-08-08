import { FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material';
import type { User } from '../../../../types';

export type StageValue = { active: boolean; approver_user_id: string };
export function ApprovalStageEditor({ number, value, users, disabled, onChange }: { number: number; value: StageValue; users: User[]; disabled: boolean; onChange: (value: StageValue) => void }) {
  return <Paper variant="outlined" sx={{ p: 2 }}><Stack spacing={1.5}><Typography fontWeight={800}>שלב {number}</Typography><FormControlLabel control={<Switch checked={value.active} disabled={disabled} onChange={(event) => onChange({ ...value, active: event.target.checked, approver_user_id: event.target.checked ? value.approver_user_id : '' })}/>} label="פעיל"/><TextField select label="מאשר" disabled={!value.active} value={value.approver_user_id} onChange={(event) => onChange({ ...value, approver_user_id: event.target.value })}>{users.filter((user) => user.is_active !== false).map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</TextField></Stack></Paper>;
}
