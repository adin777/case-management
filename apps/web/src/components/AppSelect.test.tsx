import {renderToStaticMarkup} from 'react-dom/server';
import {describe,expect,it} from 'vitest';
import {AppMultiSelect} from './AppMultiSelect';
import {AppSelect} from './AppSelect';

describe('shared selects',()=>{
  it('renders a labelled single select with valid options',()=>{const html=renderToStaticMarkup(<AppSelect label="Environment" value="1" options={[{value:'1',label:'One'}]} onChange={()=>undefined}/>);expect(html).toContain('Environment');expect(html).toContain('One')});
  it('keeps multi-select semantics for repeated selection',()=>{const html=renderToStaticMarkup(<AppMultiSelect label="Participants" value={['1']} options={[{value:'1',label:'One'},{value:'2',label:'Two'}]} onChange={()=>undefined}/>);expect(html).toContain('multiple');expect(html).toContain('Participants')});
});
