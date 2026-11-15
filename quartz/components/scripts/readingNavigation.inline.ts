// Mark an exact Obsidian block/heading target, and make backlinks find the
// paragraph in the source note that actually links to the current note.
let returnTo: { url: string; title: string } | null = null
let marked: HTMLElement | null = null

function article(): HTMLElement | null {
  return document.querySelector(".center article")
}

function headingTitle(): string {
  return document.querySelector(".page-header h1")?.textContent?.trim() || document.title
}

function contextElement(element: HTMLElement): HTMLElement {
  if (element.classList.contains("anchor-alias")) {
    return (element.nextElementSibling || element.previousElementSibling || element) as HTMLElement
  }
  return (element.closest("li, p, blockquote, h1, h2, h3, h4, h5, h6") || element) as HTMLElement
}

function mark(element: HTMLElement | null, scroll: boolean) {
  marked?.classList.remove("reading-target")
  marked = element
  if (!element) return
  element.classList.add("reading-target")
  if (scroll) {
    requestAnimationFrame(() => element.scrollIntoView({ block: "center", behavior: "smooth" }))
  }
}

function addBacklinkContexts() {
  const current = document.body.dataset.slug
  if (!current) return
  document.querySelectorAll<HTMLAnchorElement>(".backlinks a.internal").forEach((link) => {
    const url = new URL(link.href, location.href)
    url.searchParams.set("from", current)
    link.href = url.toString()
    link.title = `查看这篇笔记引用「${headingTitle()}」的原文位置`
  })
}

function openMainDirectory() {
  const tree = document.querySelector(".explorer-ul")
  if (!tree) return
  const selector = '.explorer-ul > li > .folder-container[data-folderpath*="邓珍本金匮要略全释"] + .folder-outer'
  const open = () => {
    const folder = document.querySelector<HTMLElement>(selector)
    if (!folder) return false
    folder.classList.add("open")
    return true
  }
  const observer = new MutationObserver(() => {
    if (open()) observer.disconnect()
  })
  observer.observe(tree, { childList: true, subtree: true })
  window.addCleanup(() => observer.disconnect())
}

function renderReadingNavigation(scroll: boolean) {
  const center = document.querySelector<HTMLElement>(".center")
  if (!center) return
  center.querySelector(".reading-nav")?.remove()
  marked?.classList.remove("reading-target")
  marked = null
  if (document.body.dataset.slug === "index") return

  const bar = document.createElement("nav")
  bar.className = "reading-nav"
  bar.setAttribute("aria-label", "阅读定位")

  const back = document.createElement("a")
  back.textContent = "← 返回上一处"
  back.href = returnTo?.url || `${document.body.dataset.basepath || ""}/`
  back.title = returnTo ? `返回「${returnTo.title}」` : "返回目录"
  bar.appendChild(back)

  const current = document.createElement("span")
  current.className = "reading-current"
  current.textContent = headingTitle()
  current.title = current.textContent
  bar.appendChild(current)

  const position = document.createElement("span")
  position.className = "reading-position"
  bar.appendChild(position)

  const body = article()
  const hash = decodeURIComponent(location.hash.slice(1))
  const from = new URL(location.href).searchParams.get("from")
  let targets: HTMLElement[] = []
  if (hash && body) {
    const element = document.getElementById(hash)
    if (element && body.contains(element)) targets = [contextElement(element)]
    position.textContent = targets.length ? "已定位到链接段落" : "原文位置未找到"
  } else if (from && body) {
    const links = [...body.querySelectorAll<HTMLAnchorElement>("a.internal[data-slug]")]
    targets = [...new Set(links.filter((link) => link.dataset.slug === from).map(contextElement))]
    position.textContent = targets.length ? `第 1 / ${targets.length} 处引用` : "引用位置未找到"
  }

  if (targets.length > 0) {
    let index = 0
    mark(targets[index], scroll)
    if (targets.length > 1) {
      const next = document.createElement("button")
      next.type = "button"
      next.textContent = "下一处 →"
      next.addEventListener("click", () => {
        index = (index + 1) % targets.length
        mark(targets[index], true)
        position.textContent = `第 ${index + 1} / ${targets.length} 处引用`
      })
      bar.appendChild(next)
    }
  }

  center.insertBefore(bar, center.firstChild)
}

document.addEventListener("click", (event) => {
  const link = (event.target as Element)?.closest?.("a[href]") as HTMLAnchorElement | null
  if (!link || link.dataset.noPopover === "true") return
  const destination = new URL(link.href)
  const basepath = document.body.dataset.basepath || ""
  if (destination.origin === location.origin && destination.pathname.startsWith(basepath + "/")) {
    returnTo = { url: location.href, title: headingTitle() }
  }
  setTimeout(() => renderReadingNavigation(false), 0)
}, true)

document.addEventListener("nav", () => {
  openMainDirectory()
  addBacklinkContexts()
  renderReadingNavigation(true)
})

window.addEventListener("hashchange", () => renderReadingNavigation(true))
