import { Component } from "react";
import type { ReactNode } from "react";
import { ErrorState } from "./States";

type Props = {
  children: ReactNode;
  /** What to show instead. Receives a function that tries again. */
  fallback?: (retry: () => void) => ReactNode;
  /** Change this to clear a previous failure (for example, the current page's address). */
  resetKey?: string;
};

/**
 * Keeps one broken piece of the screen from blanking the whole app. Used at three levels: the whole app,
 * each page, and each chart, so a failing chart leaves the rest of its page working.
 */
export class ErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(previous: Props) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) this.setState({ failed: false });
  }

  retry = () => this.setState({ failed: false });

  render() {
    if (!this.state.failed) return this.props.children;
    if (this.props.fallback) return this.props.fallback(this.retry);
    return (
      <ErrorState
        title="This part of the page couldn't be shown"
        message="The rest of the page still works. Try again, or reload the page if it keeps happening."
        onRetry={this.retry}
      />
    );
  }
}
