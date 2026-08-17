[33m(!) Your Vite config uses features that are unsupported by `configLoader: 'native'`, which is planned to become the default in a future major version of Vite:
  - ESM syntax in a file loaded as CommonJS (vite.config.ts:1:1). Use a `.mjs` extension or set `"type": "module"` in the closest package.json
Set `VITE_CONFIG_NATIVE_IGNORE_WARNING=true` to suppress this warning.[39m
[2m16:50:40[22m [33m[1m[vite][22m[39m [33mwarning: `esbuild` option was specified by "vite:react-babel" plugin. This option is deprecated, please use `oxc` instead.[39m
`optimizeDeps.rollupOptions` / `ssr.optimizeDeps.rollupOptions` is deprecated. Use `optimizeDeps.rolldownOptions` instead. Note that this option may be set by a plugin. Set VITE_DEPRECATION_TRACE=1 to see where it is called.
[33mBoth esbuild and oxc options were set. oxc options will be used and esbuild options will be ignored.[39m The following esbuild options were set: `{ jsx: 'automatic', jsxImportSource: undefined }`
[vite:react-babel] We recommend switching to `@vitejs/plugin-react-oxc` for improved performance. More information at https://vite.dev/rolldown

 RUN  v4.1.10 C:/Users/YUSUF ÇİNAR/OneDrive/Belgeler/Masaüstü/projelerim/Yazılım_müh/windows-ai-files


 Test Files  6 passed (6)
      Tests  100 passed (100)
   Start at  16:50:40
   Duration  3.78s (transform 1.18s, setup 4.60s, import 1.11s, tests 1.48s, environment 9.87s)

