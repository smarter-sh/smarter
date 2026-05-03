// ----------------------------------------------------------------------------
// ServiceHealth Component.
// ----------------------------------------------------------------------------
import "./styles.css";


interface ServiceHealthProps {
  apiUrl: string;
}

function ServiceHealth({ apiUrl }: ServiceHealthProps) {

  return (
    <>
      <section className="service-health" aria-label="ServiceHealth">
        <h4>Hello World {apiUrl}</h4>
      </section>
    </>
  );
}

export default ServiceHealth;
