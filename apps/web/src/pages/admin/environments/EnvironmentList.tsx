import { Add, Settings } from '@mui/icons-material';
import { Box, Button, Card, CardContent, Chip, FormControlLabel, Grid, Stack, Switch, Typography } from '@mui/material';
import type { Environment } from '../../../types';

type Props = { environments: Environment[]; selected?: Environment; activeOnly: boolean; onActiveOnlyChange: (value: boolean) => void; onSelect: (item: Environment) => void; onCreate: () => void };

export function EnvironmentList({ environments, selected, activeOnly, onActiveOnlyChange, onSelect, onCreate }: Props) {
  return <Stack spacing={2}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}>
      <Box><Typography variant="h4" fontWeight={800}>סביבות עבודה</Typography><Typography color="text.secondary">הגדרת תהליכים, שדות, הרשאות ואוטומציות</Typography></Box>
      <Button variant="contained" startIcon={<Add/>} onClick={onCreate}>סביבה חדשה</Button>
    </Stack>
    <FormControlLabel control={<Switch checked={activeOnly} onChange={(event) => onActiveOnlyChange(event.target.checked)}/>} label="הצג סביבות פעילות בלבד"/>
    <Grid container spacing={2}>{environments.map((item) => <Grid size={{ xs: 12, md: 4 }} key={item.id}>
      <Card onClick={() => onSelect(item)} sx={{ cursor: 'pointer', border: selected?.id === item.id ? '2px solid' : undefined, borderColor: 'primary.main' }}><CardContent><Stack direction="row" spacing={1.5}><Settings color="primary"/><Box><Typography variant="h6">{item.name_he}</Typography><Typography color="text.secondary">{item.name_en} · {item.system_number}</Typography><Chip size="small" color={item.is_active ? 'success' : 'default'} label={item.is_active ? 'פעילה' : 'לא פעילה'}/></Box></Stack></CardContent></Card>
    </Grid>)}</Grid>
  </Stack>;
}
