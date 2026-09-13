export function readReportState(search: URLSearchParams) {
  const filters: Record<string,string> = {};
  search.forEach((value,key)=>{if(!['page','page_size','sort','direction','run','columns'].includes(key))filters[key]=value});
  return {filters,page:Number(search.get('page')||1),pageSize:Number(search.get('page_size')||25),sort:search.get('sort')||'',direction:search.get('direction')||'asc',run:search.get('run')==='1'};
}

export function writeReportState(filters:Record<string,string>,page:number,pageSize:number,sort:string,direction:string,columns?:string[]){
  const next=new URLSearchParams();Object.entries(filters).forEach(([key,value])=>{if(value)next.set(key,value)});
  next.set('page',String(page));next.set('page_size',String(pageSize));if(sort)next.set('sort',sort);if(direction)next.set('direction',direction);if(columns?.length)next.set('columns',columns.join(','));next.set('run','1');return next;
}
