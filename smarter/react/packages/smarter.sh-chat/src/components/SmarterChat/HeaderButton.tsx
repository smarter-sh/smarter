/**
 * A button of the chat's header, as the chat's own buttons look, for the buttons that a page adds to the header with
 * SmarterChat's headerActions prop, e.g. the web console's Help and Console buttons. Its label is hidden, but still
 * names the button for screen readers, when the chat is narrow. A ref reaches the button element, e.g. to return the
 * focus to it when a menu that it opens closes.
 */
import { Button } from "@chatscope/chat-ui-kit-react";
import type { ButtonHTMLAttributes, ReactNode, Ref } from "react";

export interface HeaderButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** The button's icon, before its label. */
  icon?: ReactNode;
  children?: ReactNode;
  ref?: Ref<HTMLButtonElement>;
}

function HeaderButton({ className = "", icon, children, ...props }: HeaderButtonProps) {
  return (
    <Button
      className={["smarter-chat-toolbar-button", children ? "smarter-chat-toolbar-button-labeled" : "", className]
        .filter(Boolean)
        .join(" ")}
      icon={icon}
      {...props}
    >
      {children ? <span className="smarter-chat-toolbar-label">{children}</span> : null}
    </Button>
  );
}

export default HeaderButton;
