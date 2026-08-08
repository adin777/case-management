import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, User } from '../../../../types';
import type { EffectiveAccess } from './types';
import { levelLabel } from './types';

export function EffectivePermissionsTab({ user, environments }: { user: User; environments: Environment[] }) {
  const [environmentId, setEnvironmentId] = useState(''); const [selected, setSelected] = useState<EffectiveAccess>();
  const { data = [], isLoading } = useQuery({ queryKey: ['effective-access', user.id, environmentId], queryFn: () => api<EffectiveAccess[]>(`/access/users/${user.id}/effective-access${environmentId ? `?environment_id=${environmentId}` : ''}`) });
  return <Stack spacing={2}><TextField select label="תחולה" value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)}><MenuItem value="">כללי</MenuItem>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</TextField>{isLoading ? <Typography>טוען הרשאות...</Typography> : <Paper variant="outlined" sx={{ overflowX: 'auto' }}><Table><TableHead><TableRow><TableCell>תחום</TableCell><TableCell>אפקטיבית</TableCell><TableCell>מקור</TableCell><TableCell>תחולה</TableCell><TableCell/></TableRow></TableHead><TableBody>{data.map((row) => <TableRow key={row.domain}><TableCell>{row.domain_name}</TableCell><TableCell>{levelLabel[row.effective_level]}</TableCell><TableCell>{row.source_name}</TableCell><TableCell>{row.scope === 'global' ? 'כללי' : 'סביבה'}</TableCell><TableCell><Button onClick={() => setSelected(row)}>הצגת מקור</Button></TableCell></TableRow>)}</TableBody></Table></Paper>}
    <Dialog open={!!selected} onClose={() => setSelected(undefined)} fullWidth><DialogTitle>{selected?.domain_name}</DialogTitle><DialogContent><Stack spacing={1}>{selected?.resolution_steps.length ? selected.resolution_steps.map((step, index) => <Paper key={index} variant="outlined" sx={{ p: 1.5 }}><Typography>{step.source_name || 'חריגת משתמש'}: {levelLabel[step.level as keyof typeof levelLabel]}</Typography><Typography variant="caption">{step.scope === 'global' ? 'כללי' : 'סביבה'}</Typography></Paper>) : <Typography>לא נמצאה הרשאה בשכבות הירושה.</Typography>}<Typography fontWeight={800}>הרשאה אפקטיבית: {selected && levelLabel[selected.effective_level]}</Typography></Stack></DialogContent><DialogActions><Button onClick={() => setSelected(undefined)}>סגירה</Button></DialogActions></Dialog>
  </Stack>;
}
