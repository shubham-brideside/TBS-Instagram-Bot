"""Helpers for `is_course_or_class_enquiry` — avoid false positives on real customer questions."""


def is_customer_asking_vendor_service_menu(message: str) -> bool:
    """
    True when the sender is asking what services the vendor offers (their menu / scope).
    These must not be classified as skip-bucket (course/collab/ad) spam.
    """
    message_lower = message.lower().strip()
    phrases = (
        "what services do you offer",
        "what services do you provide",
        "what services do you have",
        "which services do you offer",
        "which services do you provide",
        "what are your services",
        "tell me about your services",
        "list your services",
        "what all services",
        "what kind of services do you",
        "services do you offer",
        "services do you provide",
    )
    return any(p in message_lower for p in phrases)
