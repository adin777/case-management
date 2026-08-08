import { Add, Edit } from '@mui/icons-material';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import type { Role } from '../../../types';

export function RolesTab({ roles, onCreate, onEdit }: { roles: Role[]; onCreate: () => void; onEdit: (role: Role) => void }) {
  return <Stack spacing={2}><Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<Add/>} onClick={onCreate}>תפקיד חדש</Button><Typography color="text.secondary">תפקידים מגדירים את ההקשר העסקי של המשתמש בסביבה. הרשאות מנוהלות דרך קבוצות וחריגות משתמש.</Typography>{roles.map((role) => <Paper key={role.id} variant="outlined" sx={{ p: 2, opacity: role.is_active ? 1 : .6 }}><Stack direction="row" justifyContent="space-between"><Box><Typography fontWeight={800}>{role.name_he || role.name}</Typography><Typography color="text.secondary">{role.description_he || role.description || 'ללא תיאור'}</Typography></Box><Button startIcon={<Edit/>} onClick={() => onEdit(role)}>עריכה</Button></Stack></Paper>)}</Stack>;
}
