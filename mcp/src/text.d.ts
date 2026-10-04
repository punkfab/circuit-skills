// esbuild's text loader: the CLI bundle embeds pcb-layout's gate scripts.
declare module "*.py" {
  const source: string;
  export default source;
}
