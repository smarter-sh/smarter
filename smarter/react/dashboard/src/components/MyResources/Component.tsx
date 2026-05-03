// ----------------------------------------------------------------------------
// MyResources Component.
// ----------------------------------------------------------------------------
import "./styles.css";


interface MyResourcesProps {
  apiUrl: string;
}

function MyResources({ apiUrl }: MyResourcesProps) {

  return (
    <>
      <section className="my-resources" aria-label="My Resources">
        <h4>Hello World {apiUrl}</h4>
      </section>
    </>
  );
}

export default MyResources;
