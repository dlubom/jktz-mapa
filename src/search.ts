import {escapeHtml as e, normalize, searchCatalogEntries} from './catalog.ts';
import type {CatalogSearchResult} from './catalog.ts';
import type {Catalog} from './types.ts';

type OpenEntry=(id:string)=>void|Promise<void>;
export interface CatalogSearchController {
  close(restoreFocus?:boolean):void;
  destroy():void;
}

export function mountCatalogSearch(catalog:Catalog,input:HTMLInputElement,results:HTMLElement,onObject:OpenEntry,onCave:OpenEntry):CatalogSearchController {
  let matches:CatalogSearchResult[]=[];
  let activeIndex=-1;
  results.id ||= `${input.id||'catalog'}-results`;
  results.setAttribute('role','listbox');
  results.setAttribute('aria-label','Wyniki wyszukiwania');
  input.setAttribute('role','combobox');
  input.setAttribute('aria-autocomplete','list');
  input.setAttribute('aria-haspopup','listbox');
  input.setAttribute('aria-controls',results.id);
  input.setAttribute('aria-expanded','false');

  function markActive(scroll=false){
    const options=results.querySelectorAll<HTMLButtonElement>('.result');
    options.forEach((option,index)=>{
      option.classList.toggle('is-active',index===activeIndex);
      option.setAttribute('aria-selected',String(index===activeIndex));
    });
    const active=options[activeIndex];
    if(active){
      input.setAttribute('aria-activedescendant',active.id);
      if(scroll)active.scrollIntoView({block:'nearest'});
    }else input.removeAttribute('aria-activedescendant');
  }
  function close(restoreFocus=false){
    results.hidden=true;
    input.setAttribute('aria-expanded','false');
    activeIndex=-1;
    markActive();
    if(restoreFocus)input.focus({preventScroll:true});
  }
  function materialBadges(result:CatalogSearchResult){
    const badges=[
      result.planCount?`<span class="badge" title="Liczba planów: ${result.planCount}">Plan</span>`:'',
      result.modelCount?`<span class="badge" title="Liczba ciągów: ${result.modelCount}">Ciąg</span>`:'',
    ].filter(Boolean).join('');
    return badges||'<span class="result-no-materials">Brak jawnie powiązanego planu i ciągu</span>';
  }
  function render(){
    matches=searchCatalogEntries(catalog,input.value);
    activeIndex=-1;
    if(!normalize(input.value)){
      results.innerHTML='';
      close();
      return;
    }
    results.hidden=false;
    input.setAttribute('aria-expanded','true');
    results.innerHTML=`<p class="result-count" role="status">${matches.length?`Liczba wyników: ${matches.length}`:'Brak wyników. Spróbuj innej nazwy lub identyfikatora.'}</p>${matches.map((result,index)=>{
      const {entry}=result;
      const context=result.kind==='object'?(result.entry.caveName&&result.entry.caveName!==entry.name?` · ${e(result.entry.caveName)}`:''):` · Otwory: ${result.entry.objectIds.length}`;
      return `<button type="button" class="result" id="${e(results.id)}-option-${index}" role="option" tabindex="-1" aria-selected="false" data-${result.kind}="${e(entry.id)}" data-search-index="${index}"><span class="result-heading"><strong>${e(entry.name)}</strong><span class="result-type">${result.kind==='object'?'Otwór / lokalizacja':'Jaskinia'}</span></span><span class="result-identity">${e(entry.id)}${context}</span><span class="result-materials">${materialBadges(result)}</span></button>`;
    }).join('')}`;
    markActive();
  }
  function choose(index:number){
    const result=matches[index];
    if(!result||results.hidden)return;
    close();
    void (result.kind==='object'?onObject:onCave)(result.entry.id);
  }
  function keydown(event:KeyboardEvent){
    if(event.isComposing)return;
    if(event.key==='Escape'){
      event.preventDefault();
      event.stopPropagation();
      close(true);
      return;
    }
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      if(results.hidden)render();
      if(!matches.length)return;
      event.preventDefault();
      const next=activeIndex<0?0:activeIndex+(event.key==='ArrowDown'?1:-1);
      activeIndex=Math.max(0,Math.min(matches.length-1,next));
      markActive(true);
      return;
    }
    if(event.key==='Enter'&&!results.hidden&&matches.length){
      event.preventDefault();
      event.stopPropagation();
      choose(activeIndex<0?0:activeIndex);
    }
  }
  function resultClick(event:MouseEvent){
    const button=event.target instanceof Element?event.target.closest<HTMLButtonElement>('[data-search-index]'):null;
    if(!button||!results.contains(button))return;
    // Main delegates object and cave actions too; dispatch each result only once.
    event.stopPropagation();
    choose(Number(button.dataset.searchIndex));
  }
  function resultFocus(event:FocusEvent){
    const button=event.target as HTMLElement;
    if(button.dataset.searchIndex===undefined)return;
    activeIndex=Number(button.dataset.searchIndex);
    markActive();
  }
  function focusLeavesSearch(event:FocusEvent){
    const next=event.relatedTarget;
    if(next===input||(next instanceof Node&&results.contains(next)))return;
    close();
  }
  input.addEventListener('input',render);
  input.addEventListener('keydown',keydown);
  input.addEventListener('focusout',focusLeavesSearch);
  results.addEventListener('keydown',keydown);
  results.addEventListener('click',resultClick);
  results.addEventListener('focusin',resultFocus);
  results.addEventListener('focusout',focusLeavesSearch);
  return {close,destroy(){
    close();
    input.removeEventListener('input',render);
    input.removeEventListener('keydown',keydown);
    input.removeEventListener('focusout',focusLeavesSearch);
    results.removeEventListener('keydown',keydown);
    results.removeEventListener('click',resultClick);
    results.removeEventListener('focusin',resultFocus);
    results.removeEventListener('focusout',focusLeavesSearch);
  }};
}
