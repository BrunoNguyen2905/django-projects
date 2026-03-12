"""Shared music taxonomy for search filters (genre, instrument, characteristic, mood)."""
from __future__ import annotations

from typing import Optional

from search_orchestration.adapters.ai.state import Taxonomy

# Fixed taxonomy for music classification (used by selection LLM and explain prompts)
MUSIC_TAXONOMY: Taxonomy = {
    "genre": [
        "8-Bit", "Acoustic", "African", "Alternative", "Ambient", "Ballad", "Big Band",
        "Bluegrass", "Blues", "Bollywood", "Caribbean", "Celtic", "Cinematic", "Classical",
        "Classic Rock", "Corporate", "Country", "Drum & Bass", "Dub Step", "East Asian",
        "EDM", "Electronic", "European", "Experimental", "Folk", "Funk", "Gospel",
        "Hard Rock", "Hip Hop", "Holiday", "House", "Indie", "Jazz", "Latin", "Lo-Fi",
        "Metal", "Middle East", "Modern Orchestral", "New Orleans / Dixieland", "Orchestral",
        "Pop", "Punk", "Rap", "R&B", "Reggae", "Rock", "Score", "Soul / Motown",
        "Soundscape", "Soundtrack / Cinematic", "Southern Rock", "Surf Rock", "Synthwave",
        "Traditional Country", "Trap", "Tribal", "Underscore", "Western", "World"
    ],
    "instrument": [
        "Accordion", "Acoustic Guitar", "Ambient Tones", "Banjo", "Bass", "Bass Guitar",
        "Bells", "Big Drums", "Cello", "Claps / Snaps / Stomps", "Drum Kit", "Drums",
        "Electric Guitar", "Electronic Drums", "Guitar", "Harmonica", "Harp", "Horns",
        "Organ", "Percussion", "Piano", "Rhodes", "Samples", "Saxophone", "Steel Guitar",
        "Strings", "Synth", "Synth Bass", "Ukulele", "Upright Bass", "Violin", "Whistling",
        "Woodwinds", "Xylophone / Mallets"
    ],
    "characteristic": [
        "Aggressive", "Atmospheric", "Beautiful", "Building", "Chaotic", "Childlike",
        "Cruising", "Dancey", "Dark", "Dreamy", "Droning", "Dynamic", "Epic", "Intense",
        "Mellow", "Minimal", "Rebellious", "Retro", "Soaring", "Sophisticated", "Soulful", "Upbeat"
    ],
    "mood": [
        "Angry", "Calm", "Chill", "Fun", "Happy", "Hopeful", "Inspiring", "Quirky",
        "Reflective", "Romantic", "Sad", "Scary", "Suspenseful"
    ]
}

SFX_TAXONOMY: Taxonomy = {
    "animals": [
        "insects", "cats", "birds", "reptiles", "dogs", "rodents", "wildlife", "farm animals", "amphibians"
    ],
    "ambience": [
        "rooms", "rural", "crowds", "nature", "city", "indoors", "weather", "suburban"
    ],
    "cartoon": [
        "percussive", "voices", "boings & dings", "toys", "melodic"
    ],
    "cinematic": [
        "impacts", "risers", "percussive", "tension", "soundscapes", "abstract", "whooshes", "scrapes", "transitions", "stingers", "reversed", "bass", "hits"
    ],
    "destruction": [
        "shattering", "war", "explosions", "crashes", "demolition", "debris"
    ],
    "electronics": [
        "phones", "radios", "computers", "cameras", "tvs", "recording"
    ],
    "elements": [
        "water", "fire", "electricity", "earth", "ice", "air", "extreme"
    ],
    "footsteps": [
        "stairs", "marching", "indoors", "shoes", "outdoors", "running", "walking", "jumping", "turning"
    ],
    "gaming": [
        "8-bit", "consoles", "effects", "musical"
    ],
    "hits": [
        "slaps", "punches", "kicks", "body falls", "body damage"
    ],
    "home": [
        "doors", "outdoors", "indoors", "appliances", "windows", "bathroom", "cooking", "drawers"
    ],
    "horror": [
        "gore", "elements & textures", "ghosts", "creatures"
    ],
    "human": [
        "bodily functions", "women", "crowds", "men", "kids", "reactions"
    ],
    "impacts": [
        "hard", "long", "cinematic", "short", "airy"
    ],
    "industry": [
        "construction", "machines", "agriculture", "factory", "tools"
    ],
    "materials": [
        "wood", "metal", "synthetic", "glass", "fabric", "paper", "stone"
    ],
    "movement": [
        "slow", "rustling", "opening", "closing", "handling", "bouncing", "sliding", "fast", "scraping", "wobbling", "pulling", "spinning", "pushing", "shaking", "rolling"
    ],
    "musical": [
        "synthesizers", "jingles", "percussion", "stingers", "guitars", "hits", "orchestral"
    ],
    "office": [],
    "sci-fi": [
        "aliens", "drones", "ambience", "machines", "weapons", "spaceships"
    ],
    "sports": [
        "extreme sports", "ball sports", "water sports", "fitness", "motorized sports"
    ],
    "technology": [
        "menus", "alerts", "interfaces", "glitches"
    ],
    "transitions": [
        "risers", "reversed", "downers", "whooshes"
    ],
    "transportation": [
        "emergency vehicles", "boats", "motorcycles", "public transit", "military", "bicycles", "trucks", "cars", "airplanes"
    ],
    "weapons": [
        "sci-fi", "military", "guns", "medieval", "explosives", "blades"
    ],
    "sound design": []
}

# SFX taxonomy with Soundstripe category and subcategory IDs
SFX_TAXONOMY_WITH_IDS = {
    "animals": {
        "id": 1,
        "subcategories": {
            "insects": 134,
            "cats": 90,
            "birds": 40,
            "reptiles": 33,
            "dogs": 50,
            "rodents": 141,
            "wildlife": 67,
            "farm animals": 52,
            "amphibians": 165
        }
    },
    "ambience": {
        "id": 2,
        "subcategories": {
            "rooms": 154,
            "rural": 30,
            "crowds": 80,
            "nature": 85,
            "city": 88,
            "indoors": 105,
            "weather": 176,
            "suburban": 100
        }
    },
    "cartoon": {
        "id": 3,
        "subcategories": {
            "percussive": 38,
            "voices": 96,
            "boings & dings": 37,
            "toys": 84,
            "melodic": 135
        }
    },
    "cinematic": {
        "id": 4,
        "subcategories": {
            "impacts": 148,
            "risers": 132,
            "percussive": 140,
            "tension": 41,
            "soundscapes": 26,
            "abstract": 51,
            "whooshes": 57,
            "scrapes": 72,
            "transitions": 78,
            "stingers": 98,
            "reversed": 119,
            "bass": 60,
            "hits": 177
        }
    },
    "destruction": {
        "id": 5,
        "subcategories": {
            "shattering": 163,
            "war": 187,
            "explosions": 62,
            "crashes": 58,
            "demolition": 95,
            "debris": 63
        }
    },
    "electronics": {
        "id": 6,
        "subcategories": {
            "phones": 61,
            "radios": 129,
            "computers": 89,
            "cameras": 64,
            "tvs": 70,
            "recording": 157
        }
    },
    "elements": {
        "id": 7,
        "subcategories": {
            "water": 147,
            "fire": 144,
            "electricity": 150,
            "earth": 138,
            "ice": 168,
            "air": 181,
            "extreme": 184
        }
    },
    "footsteps": {
        "id": 8,
        "subcategories": {
            "stairs": 116,
            "marching": 167,
            "indoors": 66,
            "shoes": 158,
            "outdoors": 82,
            "running": 81,
            "walking": 110,
            "jumping": 131,
            "turning": 122
        }
    },
    "gaming": {
        "id": 9,
        "subcategories": {
            "8-bit": 94,
            "consoles": 118,
            "effects": 121,
            "musical": 54
        }
    },
    "hits": {
        "id": 10,
        "subcategories": {
            "slaps": 169,
            "punches": 76,
            "kicks": 152,
            "body falls": 31,
            "body damage": 75
        }
    },
    "home": {
        "id": 11,
        "subcategories": {
            "doors": 47,
            "outdoors": 43,
            "indoors": 46,
            "appliances": 65,
            "windows": 91,
            "bathroom": 102,
            "cooking": 107,
            "drawers": 99
        }
    },
    "horror": {
        "id": 12,
        "subcategories": {
            "gore": 173,
            "elements & textures": 151,
            "ghosts": 171,
            "creatures": 143
        }
    },
    "human": {
        "id": 13,
        "subcategories": {
            "bodily functions": 124,
            "women": 106,
            "crowds": 123,
            "men": 27,
            "kids": 128,
            "reactions": 120
        }
    },
    "impacts": {
        "id": 14,
        "subcategories": {
            "hard": 77,
            "long": 86,
            "cinematic": 108,
            "short": 48,
            "airy": 137
        }
    },
    "industry": {
        "id": 15,
        "subcategories": {
            "construction": 87,
            "machines": 112,
            "agriculture": 42,
            "factory": 114,
            "tools": 188
        }
    },
    "materials": {
        "id": 16,
        "subcategories": {
            "wood": 103,
            "metal": 156,
            "synthetic": 153,
            "glass": 161,
            "fabric": 148,
            "paper": 97,
            "stone": 160
        }
    },
    "movement": {
        "id": 17,
        "subcategories": {
            "slow": 73,
            "rustling": 145,
            "opening": 79,
            "closing": 162,
            "handling": 115,
            "bouncing": 109,
            "sliding": 45,
            "fast": 49,
            "scraping": 35,
            "wobbling": 32,
            "pulling": 56,
            "spinning": 155,
            "pushing": 68,
            "shaking": 164,
            "rolling": 146
        }
    },
    "musical": {
        "id": 18,
        "subcategories": {
            "synthesizers": 101,
            "jingles": 36,
            "percussion": 53,
            "stingers": 55,
            "guitars": 69,
            "hits": 117,
            "orchestral": 104
        }
    },
    "office": {"id": 19, "subcategories": {}},
    "sci-fi": {
        "id": 20,
        "subcategories": {
            "aliens": 186,
            "drones": 166,
            "ambience": 175,
            "machines": 179,
            "weapons": 182,
            "spaceships": 185
        }
    },
    "sports": {
        "id": 21,
        "subcategories": {
            "extreme sports": 180,
            "ball sports": 125,
            "water sports": 111,
            "fitness": 174,
            "motorized sports": 133
        }
    },
    "technology": {
        "id": 22,
        "subcategories": {
            "menus": 83,
            "alerts": 34,
            "interfaces": 93,
            "glitches": 92
        }
    },
    "transitions": {
        "id": 23,
        "subcategories": {
            "risers": 161,
            "reversed": 136,
            "downers": 178,
            "whooshes": 74
        }
    },
    "transportation": {
        "id": 24,
        "subcategories": {
            "emergency vehicles": 172,
            "boats": 159,
            "motorcycles": 71,
            "public transit": 130,
            "military": 113,
            "bicycles": 183,
            "trucks": 126,
            "cars": 142,
            "airplanes": 170
        }
    },
    "weapons": {
        "id": 25,
        "subcategories": {
            "sci-fi": 39,
            "military": 44,
            "guns": 59,
            "medieval": 139,
            "explosives": 149,
            "blades": 127
        }
    },
    "sound design": {"id": 189, "subcategories": {}}
}


def get_taxonomy_summary_for_prompts(taxonomy: Taxonomy, max_examples: Optional[int] = None) -> str:
    """Build a summary of categories and terms for use in explain prompts for any taxonomy.
    If max_examples is None, include every term; otherwise show that many per category plus '...'.
    """
    parts = []
    for category, terms in taxonomy.items():
        label = category.capitalize()
        if max_examples is None:
            examples = ", ".join(terms)
        else:
            examples = ", ".join(terms[:max_examples])
            if len(terms) > max_examples:
                examples += ", ..."
        parts.append(f"{label}: {examples}")
    return " | ".join(parts)
