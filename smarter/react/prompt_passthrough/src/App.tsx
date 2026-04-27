import Hero from "./components/Hero";
import Prompt from "./components/Prompt";
import Response from "./components/Response";

function App() {
  return (
    <>
      <Hero />
      <section id="next-steps" className="container">
        <div className="row g-5 d-flex mb-5">
          <Prompt />
        </div>
        <div className="row g-5 d-flex">
          <Response />
        </div>
      </section>
      <div className="my-5"></div>
      <section id="spacer"></section>
    </>
  );
}

export default App;
