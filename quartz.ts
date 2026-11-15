import { loadQuartzConfig, loadQuartzLayout } from "./quartz/plugins/loader/config-loader"
import { componentRegistry } from "./quartz/components/registry"

type ExplorerNode = {
  slugSegments?: string[]
  slugSegment?: string
  displayName?: string
  isFolder?: boolean
  children: ExplorerNode[]
}

// The published content is already limited to the outgoing-link closure of chapters 1–9.
// Show every published note in four useful reading groups without adding vault files.
componentRegistry.setOptionOverrides("@quartz-community/explorer", {
  filterFn: (node: ExplorerNode) => !["index", "tags"].includes(node.slugSegment ?? ""),
  sortFn: (a: ExplorerNode, b: ExplorerNode) => {
    const pathA = a.slugSegments?.join("/") ?? ""
    const pathB = b.slugSegments?.join("/") ?? ""
    const rankA = pathA === "注解金匱要略/邓珍本金匮要略全释" ? 0
      : pathA === "医案" ? 1 : pathA === "注解金匱要略" ? 2 : pathA === "经典" ? 3 : 10
    const rankB = pathB === "注解金匱要略/邓珍本金匮要略全释" ? 0
      : pathB === "医案" ? 1 : pathB === "注解金匱要略" ? 2 : pathB === "经典" ? 3 : 10
    if (rankA !== rankB) return rankA - rankB
    if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1
    return (a.displayName ?? a.slugSegment ?? "").localeCompare(
      b.displayName ?? b.slugSegment ?? "", "zh-CN", { numeric: true },
    )
  },
  mapFn: (node: ExplorerNode) => {
    if ((node.slugSegments?.length ?? 0) === 0) {
      const annotations = node.children.find((child) => child.slugSegment === "注解金匱要略")
      const main = annotations?.children.find((child) => child.slugSegment === "邓珍本金匮要略全释")
      if (main && annotations) {
        annotations.children = annotations.children.filter((child) => child !== main)
        main.displayName = "邓珍本 · 第一至九篇"
      }
      const cases = node.children.find((child) => child.slugSegment === "医案")
      const classics = node.children.find((child) => child.slugSegment === "经典")
      if (annotations) annotations.displayName = "金匮注解与原文"
      if (classics) classics.displayName = "经典引文"
      node.children = [main, cases, annotations, classics].filter(
        (child): child is ExplorerNode => child !== undefined && child.children.length > 0,
      )
    }
    return node
  },
})

const config = await loadQuartzConfig()
export default config
export const layout = await loadQuartzLayout()
