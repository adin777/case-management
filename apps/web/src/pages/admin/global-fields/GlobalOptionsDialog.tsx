import { useState } from 'react';
import { DndContext, closestCenter, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { DeleteOutline, DragIndicator } from '@mui/icons-material';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Stack, Switch, TextField, Typography } from '@mui/material';
import type { GlobalField, GlobalOption } from './types';

function OptionRow({ option, onUpdate, onRemove }: { option: GlobalOption; onUpdate: (option: GlobalOption, label: string, active: boolean) => void; onRemove: (option: GlobalOption) => void }) {
  const sortable=useSortable({id:option.id}); const [label,setLabel]=useState(option.label_he);
  return <Stack ref={sortable.setNodeRef} direction="row" gap={1} alignItems="center" sx={{p:1.25,border:'1px solid',borderColor:'divider',borderRadius:2.5,transform:CSS.Transform.toString(sortable.transform),transition:sortable.transition,bgcolor:'#fff'}}><IconButton {...sortable.attributes} {...sortable.listeners} aria-label={`גרירת ${option.label_he}`}><DragIndicator/></IconButton><TextField size="small" fullWidth label="שם ערך" value={label} onChange={e=>setLabel(e.target.value)} onBlur={()=>label.trim()&&label!==option.label_he&&onUpdate(option,label,option.is_active)}/><Switch checked={option.is_active} onChange={e=>onUpdate(option,label,e.target.checked)}/><IconButton color="error" aria-label="מחיקה" onClick={()=>onRemove(option)}><DeleteOutline/></IconButton></Stack>;
}
export function GlobalOptionsDialog({ field, onClose, onAdd, onUpdate, onRemove, onReorder }: { field?: GlobalField; onClose: () => void; onAdd: (label: string) => Promise<void>; onUpdate: (option: GlobalOption, label: string, active: boolean) => void; onRemove: (option: GlobalOption) => void; onReorder: (ids: string[]) => void }) {
  const [label,setLabel]=useState(''); if(!field)return null;
  const drag=(event:DragEndEvent)=>{if(!event.over||event.active.id===event.over.id)return;const next=arrayMove(field.options,field.options.findIndex(x=>x.id===event.active.id),field.options.findIndex(x=>x.id===event.over?.id));onReorder(next.map(x=>x.id));};
  return <Dialog open onClose={onClose} fullWidth maxWidth="sm"><DialogTitle>ניהול ערכים · {field.label_he}</DialogTitle><DialogContent><Typography color="text.secondary" mb={2}>הסדר נשמר באמצעות גרירה. ערך שנמצא בשימוש יושבת במקום להימחק.</Typography><DndContext collisionDetection={closestCenter} onDragEnd={drag}><SortableContext items={field.options.map(x=>x.id)} strategy={verticalListSortingStrategy}><Stack spacing={1}>{field.options.map(option=><OptionRow key={option.id} option={option} onUpdate={onUpdate} onRemove={onRemove}/>)}</Stack></SortableContext></DndContext><Stack direction="row" gap={1} mt={2}><TextField fullWidth label="ערך חדש" value={label} onChange={e=>setLabel(e.target.value)}/><Button variant="contained" disabled={!label.trim()} onClick={async()=>{await onAdd(label);setLabel('')}}>הוספה</Button></Stack></DialogContent><DialogActions><Button onClick={onClose}>סגירה</Button></DialogActions></Dialog>;
}
