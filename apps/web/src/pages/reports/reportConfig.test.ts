import {describe,expect,it} from 'vitest';
import {approvalStatusHe,reportFields} from './reportConfig';

describe('operational report configuration',()=>{
  it('defines visible labels and real selector types for every approval filter',()=>{
    expect(reportFields.approvals.every(field=>field.label.trim().length>0)).toBe(true);
    expect(Object.fromEntries(reportFields.approvals.map(field=>[field.key,field.type]))).toMatchObject({
      environment_id:'environment',request_type_id:'request_type',approver_id:'user',
      status:'approval_status',step:'approval_step'
    });
  });
  it('defines readable user filters and every approval status in Hebrew',()=>{
    expect(reportFields.users.map(field=>field.label)).toEqual([
      'שם','Email','Username','סטטוס','מקור','מחלקה','תפקיד ארגוני','קבוצה','סביבה'
    ]);
    expect(approvalStatusHe).toEqual({pending:'ממתין לאישור',approved:'אושר',rejected:'נדחה',cancelled:'בוטל',superseded:'הוחלף'});
  });
});
