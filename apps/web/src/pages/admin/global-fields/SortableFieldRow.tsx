import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { DragIndicator, ListAlt, MoreHoriz } from '@mui/icons-material';
import { Button, Chip, IconButton, TableCell, TableRow, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { semanticLabel, typeLabel, type GlobalField } from './types';

export function SortableFieldRow({ row, onMenu, onManageOptions }: {
  row: GlobalField;
  onMenu: (anchor: HTMLElement, row: GlobalField) => void;
  onManageOptions: (row: GlobalField) => void;
}) {
  const { t, i18n } = useTranslation();
  const sortable = useSortable({ id: row.id });
  const name = i18n.language === 'he' ? row.label_he : row.label_en || row.label_he;
  const isSelect = ['single_select', 'multi_select'].includes(row.field_type);
  const label = (key: string) => t(`globalFieldsList.${key}`);
  return <TableRow ref={sortable.setNodeRef} sx={{ transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition, bgcolor: 'background.paper' }}>
    <TableCell className="record-drag"><IconButton {...sortable.attributes} {...sortable.listeners} sx={{ touchAction: 'none' }} aria-label={t('globalFieldsList.drag', { name })}><DragIndicator /></IconButton></TableCell>
    <TableCell className="record-title"><Typography fontWeight={650}>{name}</Typography></TableCell>
    <TableCell data-label={label('purpose')}>{semanticLabel(row.semantic_binding)}</TableCell>
    <TableCell data-label={label('type')}>{typeLabel(row.field_type)}</TableCell>
    <TableCell data-label={label('values')}>{isSelect ? <Button size="small" startIcon={<ListAlt />} onClick={() => onManageOptions(row)}>{t('globalFieldsList.manage', { count: row.options.length })}</Button> : label('none')}</TableCell>
    <TableCell data-label={label('status')}><Chip size="small" color={row.is_active ? 'success' : 'default'} label={label(row.is_active ? 'active' : 'inactive')} /></TableCell>
    <TableCell data-label={label('required')}>{label(row.is_required ? 'yes' : 'no')}</TableCell>
    <TableCell data-label={label('create')}>{label('yes')}</TableCell>
    <TableCell data-label={label('edit')}>{label('yes')}</TableCell>
    <TableCell data-label={label('order')}>{row.sort_order + 1}</TableCell>
    <TableCell className="record-actions"><IconButton aria-label={`${label('actions')}: ${name}`} onClick={event => onMenu(event.currentTarget, row)}><MoreHoriz /></IconButton></TableCell>
  </TableRow>;
}
