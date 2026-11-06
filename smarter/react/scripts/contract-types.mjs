/**
 * Generates a package's src/contract.gen.ts, the TypeScript types of one of its Smarter backend contracts,
 * from the contract's JSON Schema in the package's contract/ folder.
 *
 * The backend generates each schema from Pydantic models, and a `make <name>-contract` target copies it into
 * the package. Each package's scripts/contract-types.mjs calls runContractTypes() with its own names, and its
 * src/contract.test.ts fails if src/contract.gen.ts is out of date:
 *
 *     npm run contract:types                    # writes src/contract.gen.ts
 *     node scripts/contract-types.mjs --check   # exits 1 if src/contract.gen.ts is out of date
 *
 * Smarter Chat (packages/smarter.sh-chat) keeps its own copy: it is published to npm, and builds on its own.
 */
import fs from "node:fs";
import path from "node:path";
import { compile } from "json-schema-to-typescript";

/**
 * The schema without the titles of its fields, which Pydantic adds to every field, and which
 * json-schema-to-typescript would otherwise turn into a named type each (AppName, AppName1, ...).
 * The titles of the definitions, which are the models' names, are kept.
 */
function withoutFieldTitles(node, isDefinition = false) {
  if (Array.isArray(node)) return node.map((item) => withoutFieldTitles(item));
  if (!node || typeof node !== "object") return node;
  const result = {};
  for (const [key, value] of Object.entries(node)) {
    if (key === "title" && !isDefinition) continue;
    if (key === "$defs") {
      result[key] = Object.fromEntries(
        Object.entries(value).map(([name, def]) => [name, withoutFieldTitles(def, true)]),
      );
    } else {
      result[key] = withoutFieldTitles(value);
    }
  }
  return result;
}

/**
 * The paths of a package's contract files.
 *
 * @param {string} root - The package's folder.
 * @param {string} schemaFile - The schema's file name in contract/, e.g. "console-session.schema.json".
 */
export function contractPaths(root, schemaFile) {
  return {
    schemaPath: path.join(root, "contract", schemaFile),
    typesPath: path.join(root, "src", "contract.gen.ts"),
  };
}

/**
 * The generated TypeScript source.
 *
 * @param {object} options
 * @param {string} options.root - The package's folder.
 * @param {string} options.schemaFile - The schema's file name in contract/.
 * @param {string} options.typeName - The name of the schema's own, top-level type.
 * @param {string} options.title - What the banner calls the contract, e.g. "The web console session contract".
 */
export async function contractTypes({ root, schemaFile, typeName, title }) {
  const { schemaPath } = contractPaths(root, schemaFile);
  const banner = `/**
 * ${title}: generated from contract/${schemaFile} by
 * scripts/contract-types.mjs. Do not edit; run \`npm run contract:types\`.
 */`;
  const schema = withoutFieldTitles(JSON.parse(fs.readFileSync(schemaPath, "utf-8")), true);
  return compile(schema, typeName, {
    bannerComment: banner,
    unreachableDefinitions: true,
    additionalProperties: true,
    style: { printWidth: 120, trailingComma: "all" },
  });
}

/**
 * Write src/contract.gen.ts, or with --check, exit 1 if it is out of date.
 *
 * @param {object} options - As for contractTypes().
 */
export async function runContractTypes(options) {
  const { typesPath } = contractPaths(options.root, options.schemaFile);
  const types = await contractTypes(options);
  const relativePath = path.relative(options.root, typesPath);
  if (process.argv.includes("--check")) {
    const current = fs.existsSync(typesPath) ? fs.readFileSync(typesPath, "utf-8") : "";
    if (current !== types) {
      console.error(`${relativePath} is out of date. Run \`npm run contract:types\`.`);
      process.exit(1);
    }
  } else {
    fs.writeFileSync(typesPath, types);
    console.log(`wrote ${relativePath}`);
  }
}
