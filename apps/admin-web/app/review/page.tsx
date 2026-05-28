import ReviewQueueClient from "./review-queue-client";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function ReviewPage() {
  return <ReviewQueueClient />;
}
