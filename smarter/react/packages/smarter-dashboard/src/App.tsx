/**
 * The dashboard's development page: the dashboard in a container. See main.tsx.
 */
import Dashboard from "./components/Dashboard";
import type { AppContextInterface } from "./Types";

function App({ appContext }: { appContext: AppContextInterface }) {
  return (
    <>
      <section className="mt-5 container" id="dashboard">
        <Dashboard appContext={appContext} />
      </section>
    </>
  );
}

export default App;
