import { Fragment } from "react"

/**
 * A translated sentence with elements inside it: {name} placeholders left by
 * t() become the given nodes, so a link or bold name keeps its place in the
 * Hindi word order instead of splitting the sentence into fragments.
 *   withNodes(t("See the {link} page."), { link: <Link to="/ipd">{t("IPD")}</Link> })
 */
export function withNodes(text, nodes) {
  return String(text).split(/(\{\w+\})/g).map((part, index) => {
    const key = part.match(/^\{(\w+)\}$/)?.[1]
    return <Fragment key={index}>{key && key in nodes ? nodes[key] : part}</Fragment>
  })
}
