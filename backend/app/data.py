from .models import Venue

VENUES = [
    Venue(name="Urban Axes", category="activity", area="Union Square", estimated_cost_per_person=32, duration_minutes=75, vibe=["fun", "active"]),
    Venue(name="Museum of Science After Hours", category="activity", area="West End", estimated_cost_per_person=29, duration_minutes=120, vibe=["interesting", "indoor"]),
    Venue(name="Duo Karaoke", category="activity", area="Allston", estimated_cost_per_person=35, duration_minutes=90, vibe=["fun", "private", "romantic"]),
    Venue(name="Boston Common Sunset Walk", category="activity", area="Back Bay", estimated_cost_per_person=0, duration_minutes=60, vibe=["romantic", "scenic"]),
    Venue(name="Trattoria Example", category="restaurant", area="North End", estimated_cost_per_person=42, duration_minutes=90, vibe=["romantic", "cozy"], food_tags=["chicken options", "risotto"]),
    Venue(name="Modern Bistro", category="restaurant", area="Back Bay", estimated_cost_per_person=36, duration_minutes=80, vibe=["stylish", "fun"], food_tags=["chicken options"]),
    Venue(name="Harbor Kitchen", category="restaurant", area="Seaport", estimated_cost_per_person=48, duration_minutes=90, vibe=["romantic", "waterfront"], food_tags=["chicken options"]),
    Venue(name="Gelato Corner", category="dessert", area="North End", estimated_cost_per_person=9, duration_minutes=30, vibe=["casual", "romantic"]),
    Venue(name="Chocolate Bar", category="dessert", area="Back Bay", estimated_cost_per_person=14, duration_minutes=40, vibe=["cozy", "romantic"]),
    Venue(name="Harbor Desserts", category="dessert", area="Seaport", estimated_cost_per_person=15, duration_minutes=40, vibe=["waterfront", "stylish"]),
]

# Temporary route estimates. In Phase 2 this becomes a maps/transit API call.
AREA_TRAVEL_MINUTES = {
    ("Allston", "Back Bay"): 22,
    ("Allston", "North End"): 31,
    ("Allston", "Seaport"): 38,
    ("Back Bay", "North End"): 18,
    ("Back Bay", "Seaport"): 20,
    ("North End", "Seaport"): 17,
    ("Union Square", "Back Bay"): 26,
    ("Union Square", "North End"): 24,
    ("Union Square", "Seaport"): 33,
    ("West End", "Back Bay"): 17,
    ("West End", "North End"): 12,
    ("West End", "Seaport"): 24,
}
