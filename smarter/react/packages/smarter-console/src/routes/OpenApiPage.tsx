/**
 * /docs/openapi: the api's OpenAPI document, rendered with Scalar, which the console ships (public/scalar/) and loads
 * on this page only. See lib/scalar.
 */
import { gettext, interpolateNodes } from "@smarter/common";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { API_CONTRACT_DOCS_URL, JSON_SCHEMAS_PATH, OPENAPI_JSON_URL } from "@/lib/docs";
import { loadScalar, SCALAR_CONFIGURATION, type ScalarApp } from "@/lib/scalar";

export function OpenApiPage() {
  const reference = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let app: ScalarApp | undefined;
    let cancelled = false;
    loadScalar().then(
      (scalar) => {
        if (cancelled || !reference.current) return;
        app = scalar.createApiReference(reference.current, SCALAR_CONFIGURATION);
      },
      () => {
        if (!cancelled) setFailed(true);
      },
    );
    return () => {
      cancelled = true;
      app?.destroy?.();
    };
  }, []);

  return (
    <section>
      <h1 className="fs-2x fw-bold mb-4">{gettext("Smarter OpenAPI Contract")}</h1>
      <p className="fs-5 text-gray-700">
        {interpolateNodes(
          gettext(
            "The typed OpenAPI 3.1 document of the Smarter api: the cli api, the chat api, and the REST reads. " +
              "Generate a client or an SDK from it, in any language. Authorize with an api key, as %(token)s, to " +
              "try the operations against this platform.",
          ),
          { token: <code>{"Token <api key>"}</code> },
        )}
      </p>
      <p className="fs-5 d-flex flex-wrap gap-4">
        <a href={OPENAPI_JSON_URL} download="openapi.json">
          {gettext("Download openapi.json")}
        </a>
        <Link to={JSON_SCHEMAS_PATH}>{gettext("SAM JSON Schemas")}</Link>
        <a href={API_CONTRACT_DOCS_URL}>{gettext("About the contract")}</a>
      </p>
      {failed && (
        <div className="alert alert-danger" role="alert">
          {gettext("The OpenAPI reference couldn't be loaded. Download openapi.json to read the document.")}
        </div>
      )}
      <div ref={reference} data-testid="openapi-reference" />
    </section>
  );
}
