export type ReportKind='approvals'|'users'|'audit';
export type ReportField={key:string;label:string;type?:string};

export const approvalStatusHe:Record<string,string>={
  pending:'ממתין לאישור',approved:'אושר',rejected:'נדחה',cancelled:'בוטל',superseded:'הוחלף'
};

export const reportFields:Record<ReportKind,ReportField[]>={
  approvals:[{key:'case_number',label:'מספר קריאה'},{key:'subject',label:'נושא'},{key:'environment_id',label:'סביבה',type:'environment'},{key:'request_type_id',label:'סוג קריאה',type:'request_type'},{key:'approver_id',label:'מאשר',type:'user'},{key:'status',label:'סטטוס אישור',type:'approval_status'},{key:'step',label:'שלב',type:'approval_step'},{key:'requested_from',label:'תאריך בקשה מ',type:'datetime-local'},{key:'requested_to',label:'תאריך בקשה עד',type:'datetime-local'},{key:'decided_from',label:'תאריך החלטה מ',type:'datetime-local'},{key:'decided_to',label:'תאריך החלטה עד',type:'datetime-local'}],
  users:[{key:'name',label:'שם'},{key:'email',label:'Email'},{key:'username',label:'Username'},{key:'status',label:'סטטוס',type:'user_status'},{key:'source',label:'מקור',type:'user_source'},{key:'department',label:'מחלקה',type:'department'},{key:'job_title',label:'תפקיד ארגוני',type:'job_title'},{key:'group_ids',label:'קבוצה',type:'group'},{key:'environment_id',label:'סביבה',type:'environment'}],
  audit:[{key:'user_id',label:'משתמש',type:'user'},{key:'effective_user_id',label:'משתמש מתחזה',type:'user'},{key:'action',label:'פעולה'},{key:'entity_type',label:'סוג ישות'},{key:'entity_id',label:'Entity ID'},{key:'environment_id',label:'סביבה',type:'environment'},{key:'date_from',label:'מתאריך',type:'datetime-local'},{key:'date_to',label:'עד תאריך',type:'datetime-local'},{key:'search',label:'חיפוש טקסט'}],
};
