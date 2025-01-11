import React from 'react';
import { Helmet } from 'react-helmet';

// add Keen menu styles from
// fix note: where do we get this bundle from, and how do we integrate to the
// bundle collected by django?
const HelmetHeadStyles = () => (
  <>
    <Helmet>
      <link
        href="https://platform.smarter.sh/static/assets/css/style.bundle.css"
        rel="stylesheet"
        type="text/css"
      />
    </Helmet>
  </>
);

export default HelmetHeadStyles;
