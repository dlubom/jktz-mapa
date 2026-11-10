import {createHash} from 'node:crypto';
import {existsSync, readFileSync} from 'node:fs';
import {defineConfig, type Plugin} from 'vite';

function versionedCatalog(): Plugin {
  let url: string | undefined;
  return {
    name: 'versioned-catalog',
    apply: 'build',
    buildStart() {
      const path = 'public/data/catalog.json';
      if (!existsSync(path)) return;
      const source = readFileSync(path);
      const digest = createHash('sha256').update(source).digest('hex');
      url = `assets/catalog.${digest}.json`;
      this.emitFile({type: 'asset', fileName: url, source});
    },
    transformIndexHtml() {
      return url ? [{tag: 'meta', attrs: {name: 'jktz-catalog', content: url}, injectTo: 'head'}] : [];
    },
  };
}

export default defineConfig({base: './', build: {target: 'es2022'}, plugins: [versionedCatalog()]});
