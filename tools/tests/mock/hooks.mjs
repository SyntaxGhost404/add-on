// Node module-resolution hooks: route the Minecraft script modules to the in-memory mocks.
const MAP = {
  "@minecraft/server": new URL("./server.mjs", import.meta.url).href,
  "@minecraft/server-ui": new URL("./server-ui.mjs", import.meta.url).href,
};

export async function resolve(specifier, context, nextResolve) {
  if (specifier in MAP) return { url: MAP[specifier], shortCircuit: true };
  return nextResolve(specifier, context);
}
