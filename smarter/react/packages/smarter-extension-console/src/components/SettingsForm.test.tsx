import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SettingsForm from "@/components/SettingsForm";
import { configureRequest } from "@/lib/settings";
import { detail, makeDetail } from "@/mocks/fixtures";

describe("SettingsForm", () => {
  it("shows each setting by its type, and whether a secret is set, without its value", () => {
    render(<SettingsForm extension={detail} busy={false} onSave={vi.fn()} />);
    expect(screen.getByText("Set, from the Secret google_maps_api_key")).toBeInTheDocument();
    expect(screen.getByLabelText(/weather_api_url/)).toHaveAttribute("type", "url");
    expect(screen.getByLabelText(/retries/)).toHaveValue(3);
    expect(screen.getByRole("switch")).not.toBeChecked();
    expect(screen.getByLabelText(/units/)).toHaveValue("");
    expect(screen.getByRole("button", { name: "Save settings" })).toBeDisabled();
  });

  it("sends only what changed, and a typed secret", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<SettingsForm extension={detail} busy={false} onSave={onSave} />);
    await user.click(screen.getByRole("switch"));
    await user.selectOptions(screen.getByLabelText(/units/), "USCS");
    await user.type(screen.getByLabelText(/weather_api_url/), "https://meteo.example.com/v1/forecast");
    await user.selectOptions(screen.getByLabelText("How to set google_maps_api_key"), "value");
    await user.type(screen.getByLabelText("New value of google_maps_api_key"), "new-key");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(onSave).toHaveBeenCalledWith({
      values: { verbose: true, units: "USCS", weather_api_url: "https://meteo.example.com/v1/forecast" },
      secrets: { google_maps_api_key: { value: "new-key" } },
    });
  });

  it("uses an existing Secret, or clears one", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<SettingsForm extension={detail} busy={false} onSave={onSave} />);
    await user.selectOptions(screen.getByLabelText("How to set google_maps_api_key"), "existing");
    await user.selectOptions(screen.getByLabelText("Secret for google_maps_api_key"), "8");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(onSave).toHaveBeenLastCalledWith({ values: {}, secrets: { google_maps_api_key: { secretId: 8 } } });
    await user.selectOptions(screen.getByLabelText("How to set google_maps_api_key"), "clear");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(onSave).toHaveBeenLastCalledWith({ values: {}, secrets: { google_maps_api_key: {} } });
  });

  it("resets a cleared value to its default", () => {
    const request = configureRequest(detail.settings, { retries: "" }, {});
    expect(request.values).toEqual({ retries: null });
  });

  it("says when there are no settings", () => {
    render(<SettingsForm extension={makeDetail({ settings: [] })} busy={false} onSave={vi.fn()} />);
    expect(screen.getByText("Weather has no settings.")).toBeInTheDocument();
  });
});
