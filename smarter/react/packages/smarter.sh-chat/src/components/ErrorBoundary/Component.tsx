/**
 * Catches a rendering error in its children, and displays a message instead of an empty page.
 */
import { Component, type ErrorInfo, type ReactNode } from "react";

import { loggerPrefix } from "@/const";
import { gettext } from "@/lib/i18n";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`${loggerPrefix} ErrorBoundary caught an error:`, error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="smarter-chat-error-boundary">
          <h2>{gettext("Something went wrong.")}</h2>

          <p>{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
