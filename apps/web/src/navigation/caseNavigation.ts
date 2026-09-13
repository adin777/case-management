import type { Location, NavigateFunction } from 'react-router-dom';

export type CaseReturnState={returnTo:string;returnLabel:string};
export function openCase(navigate:NavigateFunction,location:Location,id:string,returnLabel:string){
  navigate(`/cases/${id}`,{state:{returnTo:location.pathname+location.search,returnLabel} satisfies CaseReturnState});
}
