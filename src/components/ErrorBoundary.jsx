import { Component } from "react"
import { CircleAlert, RefreshCw, RotateCcw } from "lucide-react"
import { Button, EmptyState } from "./ui"

/**
 * Catches an error thrown while a page renders, so staff see a way out
 * instead of a blank screen (RL-08). It also covers a page chunk that fails to
 * load after a new deploy, which Reload fixes. A new ``resetKey`` (the URL)
 * clears the error, so going to another page works again.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null, resetKey: props.resetKey }
    this.reset = this.reset.bind(this)
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  static getDerivedStateFromProps(props, state) {
    if (props.resetKey !== state.resetKey) {
      return { error: null, resetKey: props.resetKey }
    }
    return null
  }

  reset() {
    this.setState({ error: null })
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert">
        <EmptyState
          icon={CircleAlert}
          title="This page could not be shown"
          description="Your work on other pages is safe. Try again, or reload the page if it keeps happening."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="secondary" icon={RotateCcw} onClick={this.reset}>Try again</Button>
              <Button icon={RefreshCw} onClick={() => window.location.reload()}>Reload page</Button>
            </div>
          }
        />
      </div>
    )
  }
}
