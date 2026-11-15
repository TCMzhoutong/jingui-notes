import { computePosition, flip, inline, shift } from "@floating-ui/dom"
import { normalizeRelativeURLs } from "../../util/path"
import { fetchCanonical } from "./util"

const p = new DOMParser()
let activeAnchor: HTMLAnchorElement | null = null

function previewBlock(element: Element): HTMLElement {
  if (element.classList.contains("anchor-alias")) {
    element = element.nextElementSibling || element
  }
  return (element.closest("li, p, blockquote, h1, h2, h3, h4, h5, h6") || element) as HTMLElement
}

function appendExcerpt(container: HTMLElement, element: Element) {
  const clone = element.cloneNode(true) as HTMLElement
  clone.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"))
  clone.removeAttribute("id")
  clone.querySelectorAll("script, iframe, button").forEach((node) => node.remove())
  if ((clone.textContent?.length || 0) > 1000) {
    const excerpt = document.createElement("p")
    excerpt.textContent = `${clone.textContent?.trim().slice(0, 1000)}…`
    container.appendChild(excerpt)
  } else {
    container.appendChild(clone)
  }
}

function buildTextPreview(
  html: Document,
  link: HTMLAnchorElement,
  hash: string,
  from: string | null,
  container: HTMLElement,
) {
  const article = html.querySelector(".center article") || html.querySelector("article.popover-hint")
  if (!article) return false

  const header = document.createElement("div")
  header.className = "popover-preview-header"
  const title = document.createElement("strong")
  title.textContent = html.querySelector(".page-header h1")?.textContent?.trim() || html.title
  header.appendChild(title)
  container.appendChild(header)

  const body = document.createElement("div")
  body.className = "popover-preview-body"
  container.appendChild(body)

  if (hash) {
    const element = html.getElementById(hash)
    if (element && article.contains(element)) {
      const block = previewBlock(element)
      if (/^H[1-6]$/.test(block.tagName)) {
        const level = Number(block.tagName.slice(1))
        appendExcerpt(body, block)
        let sibling = block.nextElementSibling
        let count = 0
        while (sibling && count < 3) {
          if (/^H[1-6]$/.test(sibling.tagName) && Number(sibling.tagName.slice(1)) <= level) break
          if (!sibling.classList.contains("anchor-alias")) {
            appendExcerpt(body, sibling)
            count++
          }
          sibling = sibling.nextElementSibling
        }
      } else {
        appendExcerpt(body, block)
      }
    } else {
      const missing = document.createElement("p")
      missing.textContent = "此链接的段落未找到，请打开原文查看。"
      body.appendChild(missing)
    }
  } else if (from) {
    const references = [...article.querySelectorAll<HTMLAnchorElement>("a.internal[data-slug]")]
      .filter((anchor) => anchor.dataset.slug === from)
      .map(previewBlock)
    const unique = [...new Set(references)]
    const label = document.createElement("small")
    label.className = "popover-preview-label"
    label.textContent = unique.length ? `引用位置 · 共 ${unique.length} 处` : "引用位置"
    body.appendChild(label)
    if (unique.length) {
      unique.slice(0, 2).forEach((element) => appendExcerpt(body, element))
      if (unique.length > 2) {
        const more = document.createElement("small")
        more.textContent = `另有 ${unique.length - 2} 处，打开原文可逐处查看。`
        body.appendChild(more)
      }
    } else {
      const missing = document.createElement("p")
      missing.textContent = "引用位置未找到，请打开原文查看。"
      body.appendChild(missing)
    }
  } else {
    const blocks = [...article.children].filter((element) =>
      /^(H[1-6]|P|BLOCKQUOTE|UL|OL)$/.test(element.tagName),
    )
    blocks.slice(0, 3).forEach((element) => appendExcerpt(body, element))
  }

  const open = document.createElement("a")
  open.className = "popover-preview-open"
  open.href = link.href
  open.textContent = hash ? "打开对应段落 →" : from ? "查看引用原文 →" : "打开全文 →"
  container.appendChild(open)
  return true
}

async function mouseEnterHandler(
  this: HTMLAnchorElement,
  { clientX, clientY }: { clientX: number; clientY: number },
) {
  const link = (activeAnchor = this)
  if (link.dataset.noPopover === "true") {
    return
  }

  async function setPosition(popoverElement: HTMLElement) {
    const { x, y } = await computePosition(link, popoverElement, {
      strategy: "fixed",
      middleware: [inline({ x: clientX, y: clientY }), shift(), flip()],
    })
    Object.assign(popoverElement.style, {
      transform: `translate(${x.toFixed()}px, ${y.toFixed()}px)`,
    })
  }

  function showPopover(popoverElement: HTMLElement) {
    clearActivePopover()
    popoverElement.classList.add("active-popover")
    setPosition(popoverElement as HTMLElement)

  }

  const targetUrl = new URL(link.href)
  const hash = decodeURIComponent(targetUrl.hash.slice(1))
  const from = targetUrl.searchParams.get("from")
  targetUrl.hash = ""
  targetUrl.search = ""
  const popoverId = `popover-${encodeURIComponent(link.pathname + link.search + link.hash)}`
  const prevPopoverElement = document.getElementById(popoverId)

  // dont refetch if there's already a popover
  if (!!document.getElementById(popoverId)) {
    showPopover(prevPopoverElement as HTMLElement)
    return
  }

  // A page fetched ahead (prefetch.inline.ts) is used as is, instead of fetching it again.
  const prefetched = await window.quartzPrefetch?.load(targetUrl)
  const response = prefetched
    ? undefined
    : await fetchCanonical(targetUrl).catch((err) => {
        console.error(err)
      })

  if (!prefetched && !response) return
  const rawContentType = prefetched?.contentType ?? response?.headers.get("Content-Type")
  if (!rawContentType) return
  const [contentType] = rawContentType.split(";")
  const [contentTypeCategory, typeInfo] = contentType.split("/")

  const popoverElement = document.createElement("div")
  popoverElement.id = popoverId
  popoverElement.classList.add("popover")
  const popoverInner = document.createElement("div")
  popoverInner.classList.add("popover-inner")
  popoverInner.dataset.contentType = contentType ?? undefined
  popoverElement.appendChild(popoverInner)

  switch (contentTypeCategory) {
    case "image":
      const img = document.createElement("img")
      img.src = targetUrl.toString()
      img.alt = targetUrl.pathname

      popoverInner.appendChild(img)
      break
    case "application":
      switch (typeInfo) {
        case "pdf":
          const pdf = document.createElement("iframe")
          pdf.src = targetUrl.toString()
          popoverInner.appendChild(pdf)
          break
        default:
          break
      }
      break
    default:
      const contents = prefetched ? (prefetched.text ?? "") : await response!.text()
      const html = p.parseFromString(contents, "text/html")
      normalizeRelativeURLs(html, targetUrl)
      if (!buildTextPreview(html, link, hash, from, popoverInner)) return
  }

  if (!!document.getElementById(popoverId)) {
    return
  }

  document.body.appendChild(popoverElement)
  if (activeAnchor !== this) {
    return
  }

  showPopover(popoverElement)
}

function clearActivePopover() {
  activeAnchor = null
  const allPopoverElements = document.querySelectorAll(".popover")
  allPopoverElements.forEach((popoverElement) => popoverElement.classList.remove("active-popover"))
}

function setupPopovers() {
  const links = [...document.querySelectorAll("a.internal")] as HTMLAnchorElement[]
  for (const link of links) {
    link.addEventListener("mouseenter", mouseEnterHandler)
    link.addEventListener("mouseleave", clearActivePopover)
    window.addCleanup(() => {
      link.removeEventListener("mouseenter", mouseEnterHandler)
      link.removeEventListener("mouseleave", clearActivePopover)
    })
  }
}

document.addEventListener("nav", setupPopovers)
document.addEventListener("render", setupPopovers)
window.addEventListener("pageshow", (event) => {
  if (!event.persisted) return
  activeAnchor = null
  document.querySelectorAll(".popover").forEach((popover) => popover.remove())
})
