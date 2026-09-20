import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { DndContext, KeyboardSensor, PointerSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment, User } from '../../../../types';
import type { SystemField, SystemFieldOption } from './types';

const blank = { code: '', label_he: '', description: '', color: '#64748b', sort_order: 0, is_active: true, is_initial: false, is_final: false, semantic_category: 'open', workflow_id: '', requires_approval: false, default_priority_id: '', default_sub_priority_id: '', default_assignee_user_id: '', default_assignee_group_id: '' };

function SortableValue({ item, children }:{item:SystemFieldOption;children:ReactNode}) {
  const {attributes,listeners,setNodeRef,transform,transition,isDragging}=useSortable({id:item.id});
  return <Paper ref={setNodeRef} {...attributes} variant="outlined" sx={{p:1.5,transform:CSS.Transform.toString(transform),transition,opacity:isDragging?.55:1}}><Stack direction="row" alignItems="center" gap={1}><Button {...listeners} aria-label={`גרירת ${item.label_he}`} sx={{minWidth:40,cursor:'grab',fontSize:20}}>☰</Button><span style={{flex:1}}>{children}</span></Stack></Paper>;
}

export function SystemFieldValuesDialog({ environment, field, onClose }: { environment: Environment; field?: SystemField; onClose: () => void }) {
  const client = useQueryClient(); const [editing, setEditing] = useState<SystemFieldOption>(); const [form, setForm] = useState(blank); const [error, setError] = useState('');
  const [ordered, setOrdered] = useState<SystemFieldOption[]>([]);
  const sensors=useSensors(useSensor(PointerSensor),useSensor(TouchSensor),useSensor(KeyboardSensor,{coordinateGetter:sortableKeyboardCoordinates}));
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  useEffect(() => { setEditing(undefined); setForm(blank); setError(''); setOrdered(field?.options || []); }, [field]);
  const choose = (item: SystemFieldOption) => { setEditing(item); setForm({ ...blank, ...item, semantic_category: item.semantic_category || 'open', workflow_id: item.workflow_id || '', default_priority_id: item.default_priority_id || '', default_sub_priority_id: item.default_sub_priority_id || '', default_assignee_user_id: item.default_assignee_user_id || '', default_assignee_group_id: item.default_assignee_group_id || '' }); };
  async function refresh() { setEditing(undefined); setForm(blank); await Promise.all([client.invalidateQueries({ queryKey: ['system-fields', environment.id] }), client.invalidateQueries({ queryKey: ['priorities', environment.id] })]); }
  async function save() {
    if (!field) return; setError(''); const code = editing ? undefined : `value_${Date.now()}`;
    try {
      const body = { ...(code && { code, environment_id: environment.id }), name_he: form.label_he, name_en: form.label_he, description: form.description || null, is_active: form.is_active, sort_order: form.sort_order, requires_approval: form.requires_approval, workflow_definition_id: null, default_priority_id: form.default_priority_id || null, default_sub_priority_id: form.default_sub_priority_id || null, default_assignee_user_id: form.default_assignee_user_id || null, default_assignee_group_id: null };
      await api(editing ? `/request-types/${editing.id}` : '/request-types', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(body) });
      await refresh();
    } catch (caught) { setError((caught as Error).message); }
  }
  async function reorder(event:DragEndEvent) { if (!field || !event.over || event.active.id===event.over.id) return; const previous=ordered; const from=previous.findIndex(item=>item.id===event.active.id); const to=previous.findIndex(item=>item.id===event.over?.id); const next=arrayMove(previous,from,to); setOrdered(next); try { await api(`/environments/${environment.id}/system-fields/${field.code}/reorder`, { method: 'PUT', body: JSON.stringify({ ids:next.map(item=>item.id) }) }); await refresh(); } catch (caught) { setOrdered(previous); setError((caught as Error).message); } }
  return <Dialog open={!!field} onClose={onClose} fullWidth maxWidth="md"><DialogTitle>ניהול ערכי {field?.label_he}</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>{error && <Alert severity="error">{error}</Alert>}
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={reorder}><SortableContext items={ordered.map(item=>item.id)} strategy={verticalListSortingStrategy}>{ordered.map((item) => <SortableValue key={item.id} item={item}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }}><span><Typography fontWeight={650}>{item.label_he}</Typography><Typography variant="body2" color="text.secondary">{item.is_active === false ? 'מושבת' : 'פעיל'}</Typography></span><Button onClick={() => choose(item)}>עריכה</Button></Stack></SortableValue>)}</SortableContext></DndContext>
    <Typography fontWeight={650}>{editing ? 'עריכת ערך' : 'ערך חדש'}</Typography><TextField label="שם" value={form.label_he} onChange={(event) => setForm({ ...form, label_he: event.target.value })}/><TextField label="תיאור" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })}/><FormControlLabel control={<Switch checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })}/>} label="פעיל"/>
    <TextField select label="מטפל ברירת מחדל" value={form.default_assignee_user_id} onChange={(event) => setForm({ ...form, default_assignee_user_id: event.target.value })}><MenuItem value="">ללא</MenuItem>{users.filter((item) => item.is_active !== false).map((item) => <MenuItem key={item.id} value={item.id}>{item.display_name}</MenuItem>)}</TextField><FormControlLabel control={<Switch checked={form.requires_approval} onChange={(event) => setForm({ ...form, requires_approval: event.target.checked })}/>} label="דורש סבב אישורים"/>
  </Stack></DialogContent><DialogActions><Button onClick={onClose}>סגירה</Button><Button variant="contained" disabled={!form.label_he.trim()} onClick={save}>שמירה</Button></DialogActions></Dialog>;
}
