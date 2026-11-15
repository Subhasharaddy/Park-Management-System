"""Shared constants for ParkCare 3D."""

STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"]
PENDING_STATUSES = ["Submitted", "Under Review", "Assigned"]   # waiting for work to start
ACTIVE_STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress"]
TRACK_STEPS = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved"]

# (name, Font Awesome icon, accent colour, short scene key)
CATEGORIES = [
    ("Broken Bench", "fa-chair", "#FF8A24"),
    ("Water Leakage", "fa-droplet", "#00D9FF"),
    ("Garbage Overflow", "fa-trash-can", "#FFD447"),
    ("Damaged Pathway", "fa-road", "#39FF88"),
    ("Broken Street Light", "fa-lightbulb", "#FFD447"),
    ("Damaged Playground", "fa-child-reaching", "#FF5C8A"),
    ("Tree Maintenance", "fa-tree", "#39FF88"),
    ("Other", "fa-circle-question", "#B58CFF"),
]
CATEGORY_NAMES = [c[0] for c in CATEGORIES]

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
