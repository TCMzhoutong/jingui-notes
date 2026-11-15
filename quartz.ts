import { loadQuartzConfig, loadQuartzLayout } from "./quartz/plugins/loader/config-loader"
import { componentRegistry } from "./quartz/components/registry"

type ExplorerNode = {
  slugSegments?: string[]
  slugSegment?: string
  children: ExplorerNode[]
}

// Keep the reading sidebar focused on the nine entry chapters. Linked reference
// notes remain searchable and accessible through ordinary links and backlinks.
componentRegistry.setOptionOverrides("@quartz-community/explorer", {
  filterFn: (node: ExplorerNode) => {
    const path = node.slugSegments?.join("/") ?? ""
    if (path === "index" || path === "注解金匱要略") return true
    const main = "注解金匱要略/邓珍本金匮要略全释"
    if (path === main) return true
    return path.startsWith(main + "/") && /^[1-9]-/.test(node.slugSegment ?? "")
  },
  mapFn: (node: ExplorerNode) => {
    if ((node.slugSegments?.length ?? 0) === 0) {
      const parent = node.children.find((child) => child.slugSegment === "注解金匱要略")
      const main = parent?.children.find((child) => child.slugSegment === "邓珍本金匮要略全释")
      node.children = [
        ...node.children.filter((child) => child.slugSegment === "index"),
        ...(main?.children ?? []),
      ]
    }
    return node
  },
})

const config = await loadQuartzConfig()
export default config
export const layout = await loadQuartzLayout()
