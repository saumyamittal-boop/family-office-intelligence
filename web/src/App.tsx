import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useSession } from "./api/hooks";
import type { SessionInfo } from "./api/client";
import { AppShell } from "./layout/AppShell";
import { ComingSoonPage } from "./pages/ComingSoonPage";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PlanPage } from "./pages/PlanPage";
import { clearFreshSignup, isFreshSignup } from "./plan/draft";
import { ErrorState, LoadingBlock } from "./ui/States";
import { WorkspaceProvider } from "./workspace/WorkspaceProvider";

/** The home page. A brand-new account (not a demo family) lands on the guided plan, as in the Streamlit app. */
function Home({ session }: { session: SessionInfo }) {
  const [fresh] = useState(isFreshSignup);
  useEffect(() => {
    if (fresh) clearFreshSignup();
  }, [fresh]);
  return fresh && !session.user.is_demo ? <Navigate to="/plan" replace /> : <OverviewPage session={session} />;
}

function SignedIn({ session }: { session: SessionInfo }) {
  return (
    <WorkspaceProvider session={session}>
      <Routes>
        <Route element={<AppShell session={session} />}>
          <Route index element={<Home session={session} />} />
          <Route path="plan" element={<PlanPage />} />
          <Route path="*" element={<ComingSoonPage />} />
        </Route>
      </Routes>
    </WorkspaceProvider>
  );
}

export default function App() {
  const session = useSession();

  if (session.isPending) {
    return (
      <main className="login">
        <LoadingBlock label="Loading" />
      </main>
    );
  }
  if (session.isError) {
    return (
      <main className="login">
        <ErrorState
          title="Can't reach the server"
          message="Check that the API is running (port 8100), then try again."
          onRetry={() => session.refetch()}
        />
      </main>
    );
  }
  return session.data ? <SignedIn session={session.data} /> : <LoginPage />;
}
