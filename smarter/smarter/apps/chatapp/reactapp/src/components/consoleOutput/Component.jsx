//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React from "react";


// Our stuff
import "./Component.css";



function ConsoleOutput(props) {

  // app configuration
  const config = props.config;    // see ../../data/sample-config.json for an example of this object.

  return (
    <div className="console-output">
      <h2>Hi Mom!!!</h2>
    </div>
  );
}

// define the props that are expected to be passed in and also
// make these immutable.
ConsoleOutput.propTypes = {};

export default ConsoleOutput;
