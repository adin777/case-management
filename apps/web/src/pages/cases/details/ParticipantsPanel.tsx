import { Close, GroupOutlined, PersonAdd } from '@mui/icons-material';
import { Avatar, Box, Button, Chip, Stack } from '@mui/material';
import type { Participant, User } from '../../../types';
import { AppSelect } from '../../../components/AppSelect';
import { CaseSection } from './CaseSection';

export function ParticipantsPanel({ participants, candidates, selected, canManage, onSelected, onAdd, onRemove }: { participants: Participant[]; candidates: User[]; selected: string; canManage: boolean; onSelected: (id: string) => void; onAdd: () => void; onRemove: (id: string) => void }) {
  return <CaseSection title="משתתפים" icon={<GroupOutlined/>}>
    <Stack direction="row" gap={1} flexWrap="wrap">
      {participants.length ? participants.map((row) => <Chip key={row.user_id} avatar={<Avatar>{row.display_name[0]}</Avatar>} label={`${row.display_name} · ${row.participant_type === 'viewer' ? 'צופה' : 'משתתף'}`} onDelete={canManage ? () => onRemove(row.user_id) : undefined} deleteIcon={canManage ? <Close/> : undefined} sx={{ height: 42, borderRadius: '8px', bgcolor: '#f7f9fc' }}/>) : <Box color="text.secondary">אין משתתפים נוספים</Box>}
    </Stack>
    {canManage && <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} mt={2.5} alignItems={{ sm: 'flex-start' }}>
      <Box sx={{ flex: 1 }}><AppSelect label="הוספת משתתף" value={selected} onChange={onSelected} options={candidates.map((user) => ({ value: user.id, label: `${user.display_name} · ${user.job_title || user.email}` }))}/></Box>
      <Button variant="outlined" startIcon={<PersonAdd/>} disabled={!selected} onClick={onAdd}>הוספה</Button>
    </Stack>}
  </CaseSection>;
}
