type Loader = (url: string, signal: AbortSignal) => Promise<ImageBitmap>;
const loadImage: Loader = async (url,signal) => {
  const response=await fetch(url,{signal});
  if(!response.ok) throw new Error(`Obraz: HTTP ${response.status}`);
  return createImageBitmap(await response.blob());
};
/** Shared decoded-image budget. Off-screen downloads are aborted; evicted bitmaps are closed. */
export class ImagePool {
  private cache = new Map<string,ImageBitmap>();
  private wanted = new Set<string>();
  private pending = new Map<string,AbortController>();
  private failed = new Set<string>();
  private closed=false;
  bytes=0;
  private concurrency:number;
  private budget:number;
  private loader:Loader;
  private changed:()=>void;
  constructor(concurrency=6,budget=64*1024*1024,loader:Loader=loadImage,changed:()=>void=()=>{}){this.concurrency=concurrency;this.budget=budget;this.loader=loader;this.changed=changed;}
  get(url:string): ImageBitmap|undefined {
    const bitmap=this.cache.get(url);
    if(bitmap){this.cache.delete(url);this.cache.set(url,bitmap);}
    return bitmap;
  }
  want(urls:string[]):void {
    this.wanted=new Set(urls);
    for(const [url,controller] of this.pending) if(!this.wanted.has(url)) controller.abort();
    this.pump();
  }
  private pump():void {
    if(this.closed)return;
    for(const url of this.wanted){
      if(this.pending.size>=this.concurrency)break;
      if(this.cache.has(url)||this.pending.has(url)||this.failed.has(url))continue;
      const controller=new AbortController();this.pending.set(url,controller);
      this.loader(url,controller.signal).then(bitmap=>{
        if(this.closed||controller.signal.aborted||!this.wanted.has(url)){bitmap.close();return;}
        const size=bitmap.width*bitmap.height*4;
        for(const [key,image] of this.cache){
          if(this.bytes+size<=this.budget)break;
          if(this.wanted.has(key))continue;
          this.cache.delete(key);this.bytes-=image.width*image.height*4;image.close();
        }
        if(this.bytes+size>this.budget){bitmap.close();this.failed.add(url);return;}
        this.cache.set(url,bitmap);this.bytes+=size;
      }).catch(error=>{if(error.name!=='AbortError')this.failed.add(url);})
        .finally(()=>{this.pending.delete(url);if(!this.closed){this.pump();this.changed();}});
    }
  }
  clear():void {this.wanted.clear();for(const c of this.pending.values())c.abort();for(const b of this.cache.values())b.close();this.cache.clear();this.bytes=0;this.failed.clear();}
  retry():void {this.failed.clear();this.pump();}
  get stats(){return {bytes:this.bytes,cached:this.cache.size,loading:this.pending.size,failed:[...this.failed].filter(url=>this.wanted.has(url)).length,wanted:this.wanted.size};}
  dispose():void {this.closed=true;for(const c of this.pending.values())c.abort();for(const b of this.cache.values())b.close();this.cache.clear();this.bytes=0;this.wanted.clear();}
}
