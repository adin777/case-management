import { Add, Edit } from '@mui/icons-material';
import { Box, Button, Chip, Paper, Stack, Typography } from '@mui/material';
import type { Role } from '../../../types';

export function RolesTab({ roles, onCreate, onEdit }: { roles: Role[]; onCreate: () => void; onEdit: (role: Role) => void }) {
  return <Stack spacing={2}><Button sx={{ alignSelf: 'flex-start' }} variant="contained" startIcon={<Add/>} onClick={onCreate}>תפקיד חדש</Button>{roles.map((role) => <Paper key={role.id} variant="outlined" sx={{ p: 2, opacity: role.is_active === false ? .6 : 1 }}><Stack direction="row" justifyContent="space-between"><Box><Typography fontWeight={800}>{role.name}</Typography><Typography color="text.secondary">{role.description || role.code}</Typography></Box><Button startIcon={<Edit/>} onClick={() => onEdit(role)}>עריכה</Button></Stack><Box>{role.permissions.map((permission) => <Chip key={permission} size="small" label={permission} sx={{ m: .25 }}/>)}</Box></Paper>)}</Stack>;
}
