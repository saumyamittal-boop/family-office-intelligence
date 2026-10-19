import "@fontsource-variable/inter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/ui.css";
import "./styles/layout.css";
import "./styles/plan.css";
import "./styles/modules.css";
import { ThemeProvider } from "./theme/ThemeProvider";
import { ErrorBoundary } from "./ui/ErrorBoundary";
import { TooltipProvider } from "./ui/Overlays";
import { ErrorState } from "./ui/States";

const queryClient = new QueryClient();

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <TooltipProvider delayDuration={300}>
            <ErrorBoundary
              fallback={() => (
                <main className="login">
                  <ErrorState
                    title="Something went wrong"
                    message="The page hit an unexpected problem. Reload to start again; nothing you saved is lost."
                    onRetry={() => window.location.reload()}
                  />
                </main>
              )}
            >
              <App />
            </ErrorBoundary>
          </TooltipProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
