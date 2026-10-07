/**
 * The MSW server that answers the API requests made in tests.
 *
 * Every request must be answered by a handler: an unhandled request fails the test. Add a
 * test's handlers with server.use(); they are removed after each test.
 */
import { setupServer } from "msw/node";

export const server = setupServer();
