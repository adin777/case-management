export type Environment={id:string;code:string;name_he:string;name_en:string;description?:string;is_active:boolean};
export type RequestType={id:string;environment_id:string;code:string;name_he:string;name_en:string;description?:string;is_active:boolean;form_version_id?:string};
export type Field={id?:string;key:string;label_he:string;label_en:string;field_type:string;is_required:boolean;is_read_only:boolean;sort_order:number;configuration_json:{options?:string[]}};
export type Form={id:string;request_type_id:string;version:number;status:'draft'|'published';fields:Field[]};
export type Comment={id:string;body:string;visibility:'public'|'internal';created_at:string};
export type CaseValue={field_definition_id:string;value_text?:string;value_number?:number;value_boolean?:boolean;value_date?:string;value_datetime?:string;value_user_id?:string;value_json?:unknown};
export type Case={id:string;case_number:string;title:string;description?:string;status:string;priority:string;created_at:string;environment_id:string;request_type_id:string;form_definition_id:string;reporter_id:string;requester_id:string;assignee_id?:string;version:number;comments:Comment[];values:CaseValue[]};
export type User={id:string;email:string;display_name:string;is_system_admin:boolean;is_active?:boolean};
