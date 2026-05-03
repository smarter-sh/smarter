// ----------------------------------------------------------------------------
// VSCodeExtension Component.
// ----------------------------------------------------------------------------
import "./styles.css";


interface VSCodeExtensionProps {
  apiUrl: string;
}

function VSCodeExtension({ apiUrl }: VSCodeExtensionProps) {

  return (
    <>
      <section className="vscode-extension" aria-label="VSCodeExtension">
        <h4>Hello World {apiUrl}</h4>
      </section>
    </>
  );
}

export default VSCodeExtension;
