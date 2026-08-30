import { Tune } from '@mui/icons-material';
import { Alert, Box, Button } from '@mui/material';
import { DynamicField } from '../../../components/DynamicField';
import type { Field, User } from '../../../types';
import { CaseSection } from './CaseSection';

export function GlobalFieldsPanel({ fields, values, users, assignees, editable, saving, onChange, onSave }: { fields: Field[]; values: Record<string, unknown>; users: User[]; assignees: User[]; editable: boolean; saving: boolean; onChange: (id: string, value: unknown) => void; onSave: () => void }) {
  const active = fields.filter((field) => field.is_active !== false);
  if (!active.length) return null;
  return <CaseSection title="שדות גלובליים" icon={<Tune/>}>
    {!editable && <Alert severity="info" sx={{ mb: 2 }}>השדות מוצגים לקריאה בלבד בהתאם להרשאות או למצב הנעילה.</Alert>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
      {active.map((field) => <DynamicField key={field.id} field={field} value={field.id ? values[field.id] : undefined} users={field.semantic_binding === 'case.assignee' ? assignees : users} disabled={!editable || field.is_read_only} onChange={(value) => field.id && onChange(field.id, value)}/>)}
    </Box>
    {editable && <Button variant="contained" disabled={saving} onClick={onSave} sx={{ mt: 2.5 }}>{saving ? 'שומר…' : 'שמירת שדות'}</Button>}
  </CaseSection>;
}
