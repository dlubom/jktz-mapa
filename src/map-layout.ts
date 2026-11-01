/** Reserve the complete overlay: capping it can put the fitted plan behind it. */
export function planFitPadding(mapTop:number,toolbarBottom:number|null):number[]{
  return [toolbarBottom===null?35:Math.max(35,toolbarBottom-mapTop+15),35,35,35];
}
