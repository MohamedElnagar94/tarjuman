declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, any>;
  export default component;
}

/** "closed" in the store build; scripts/screenshots.mjs and iframe-test.mjs build with TARJUMAN_OPEN_SHADOW=1 to look inside. */
declare const __SHADOW_MODE__: ShadowRootMode;
