import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material';
import { ApiError } from '../../../api/client';

const schema = z.object({
  name: z.string().trim().min(2, 'יש להזין שם קבוצה הכולל לפחות שני תווים'),
  description: z.string().optional(),
});
export type GroupFormValues = z.infer<typeof schema>;

export function GroupDialog({ open, saving, onClose, onSubmit }: { open: boolean; saving: boolean; onClose: () => void; onSubmit: (values: GroupFormValues) => Promise<void> }) {
  const { control, handleSubmit, reset, setError, formState: { errors } } = useForm<GroupFormValues>({ resolver: zodResolver(schema), defaultValues: { name: '', description: '' } });
  useEffect(() => { if (open) reset({ name: '', description: '' }); }, [open, reset]);
  async function submit(values: GroupFormValues) {
    try { await onSubmit(values); reset(); }
    catch (caught) { if (caught instanceof ApiError) Object.entries(caught.fieldErrors).forEach(([field, message]) => { if (field === 'name' || field === 'description') setError(field, { message }); }); }
  }
  return <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth><Stack component="form" onSubmit={handleSubmit(submit)} noValidate>
    <DialogTitle>יצירת קבוצת משתמשים</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
      <Controller name="name" control={control} render={({ field }) => <TextField {...field} autoFocus label="שם הקבוצה" required error={Boolean(errors.name)} helperText={errors.name?.message} />} />
      <Controller name="description" control={control} render={({ field }) => <TextField {...field} label="תיאור" multiline minRows={3} error={Boolean(errors.description)} helperText={errors.description?.message} />} />
    </Stack></DialogContent><DialogActions><Button onClick={onClose} disabled={saving}>ביטול</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'שומר...' : 'שמירה'}</Button></DialogActions>
  </Stack></Dialog>;
}
