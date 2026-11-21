import type {Extent,ModelEntry} from './types.ts';

const neighborDistance = 100;
const palette = ['#0068b3','#c15400','#6e48aa','#08754e','#ad365b','#70570c','#007b82'];
const pinnedColors = new Map([['WielkaSniezna',0],['SnieznaStudnia',1]]);

function extentDistance(a:Extent,b:Extent) {
  const dx = Math.max(b[0]-a[2],a[0]-b[2],0);
  const dy = Math.max(b[1]-a[3],a[1]-b[3],0);
  return Math.hypot(dx,dy);
}

export function assignModelColors(models:readonly Pick<ModelEntry,'id'|'extent'>[]):Map<string,string> {
  const nodes = new Map(models.map(model => [model.id,{
    id:model.id,
    neighbors:models.filter(other => model.id!==other.id && extentDistance(model.extent,other.extent)<=neighborDistance).map(other=>other.id),
    usedColors:new Set<number>(),
  }]));
  const colors = new Map<string,string>();
  const assign = (id:string,index:number) => {
    // Extend the palette if a later catalogue contains a denser group.
    colors.set(id,palette[index] ?? `hsl(${index * 137.508 % 360}, 72%, 38%)`);
    for(const neighbor of nodes.get(id)!.neighbors) nodes.get(neighbor)!.usedColors.add(index);
  };
  for(const [id,index] of pinnedColors) if(nodes.has(id)) assign(id,index);
  while(colors.size<nodes.size) {
    // Prioritize the model with the fewest remaining choices, then the most neighbors.
    const [node] = [...nodes.values()].filter(node=>!colors.has(node.id)).sort((a,b)=>
      b.usedColors.size-a.usedColors.size || b.neighbors.length-a.neighbors.length ||
      Number(a.id>b.id)-Number(a.id<b.id));
    let index=0;
    while(node.usedColors.has(index)) index++;
    assign(node.id,index);
  }
  return colors;
}
