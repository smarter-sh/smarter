import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { profileImageHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import ProfileImageItems from "@/components/ProfileImageItems/Component";

const apiUrl = appContext.urls.profileImageApi;

function setup() {
  const onChange = vi.fn();
  render(<ProfileImageItems sessionContext={sessionContext} apiUrl={apiUrl} fileInputId="file" onChange={onChange} />);
  return onChange;
}

const image = () => new File(["png"], "ada.png", { type: "image/png" });

describe("ProfileImageItems", () => {
  it("uploads the chosen image as a multipart form", async () => {
    const user = userEvent.setup();
    // MSW can't parse a multipart body under jsdom, so the test checks the request's content type.
    let contentType: string | null = null;
    server.use(
      http.post(apiUrl, ({ request }) => {
        contentType = request.headers.get("content-type");
        return HttpResponse.json({ profile_image_url: "https://example.com/ada.png" });
      }),
    );
    const onChange = setup();
    await user.upload(screen.getByLabelText("Change Profile Image"), image());
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledWith("https://example.com/ada.png"));
    expect(contentType).toMatch(/^multipart\/form-data/);
  });

  it("removes the image", async () => {
    const user = userEvent.setup();
    server.use(...profileImageHandlers);
    const onChange = setup();
    await user.click(screen.getByRole("button", { name: "Remove Profile Image" }));
    await vi.waitFor(() =>
      expect(onChange).toHaveBeenCalledWith("http://localhost:9357/static/images/avatars/default-profile.svg"),
    );
  });

  it("shows why an upload was rejected", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(apiUrl, () =>
        HttpResponse.json({ profile_image: ["The image must be 2 MB or smaller."] }, { status: 400 }),
      ),
    );
    const onChange = setup();
    await user.upload(screen.getByLabelText("Change Profile Image"), image());
    expect(await screen.findByRole("alert")).toHaveTextContent("The image must be 2 MB or smaller.");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows the api's error, or a generic one", async () => {
    const user = userEvent.setup();
    server.use(http.delete(apiUrl, () => HttpResponse.json({ error: "Not signed in." }, { status: 401 })));
    setup();
    await user.click(screen.getByRole("button", { name: "Remove Profile Image" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Not signed in.");
    server.use(http.delete(apiUrl, () => new HttpResponse("oops", { status: 500 })));
    await user.click(screen.getByRole("button", { name: "Remove Profile Image" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The profile image could not be saved.");
  });
});
