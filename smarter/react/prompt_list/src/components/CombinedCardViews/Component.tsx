import type { Chatbot } from "@/lib/Types";
import { CardView } from "@/components/CardView/Component";
import { renderDetailRow } from "@/lib/renderDetail";

import "./styles.css";

interface CombinedCardViewsProps {
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
}

function CombinedCardViews({ chatbots }: CombinedCardViewsProps) {
  return (
    <div>
      <div className={"card-view"}>
        <section className="row g-5 g-xl-10 mb-l-10">
          {chatbots.user.length > 0 ? (
            <CardView
              title="Your Chatbots"
              chatbots={chatbots.user}
              cardClassName="mt-15"
              renderDetailRow={renderDetailRow}
            />
          ) : null}
          <CardView
            title="Shared Chatbots"
            chatbots={chatbots.shared}
            cardClassName={chatbots.user.length > 0 ? "mt-5" : "mt-15"}
            renderDetailRow={renderDetailRow}
          />
        </section>
      </div>
    </div>
  );
}

export default CombinedCardViews;
