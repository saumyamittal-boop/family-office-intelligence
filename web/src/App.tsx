import { useSession } from "./api/hooks";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";

export default function App() {
  const session = useSession();

  if (session.isPending) return <p className="muted center">Loading…</p>;
  if (session.isError) {
    return (
      <p role="alert" className="banner bad center">
        Can't reach the server. Check that the API is running (port 8100), then reload.
      </p>
    );
  }
  return session.data ? <HomePage session={session.data} /> : <LoginPage />;
}
