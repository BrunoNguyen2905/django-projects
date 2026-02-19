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


def get_taxonomy_summary_for_prompts(max_examples: Optional[int] = None) -> str:
    """Build a summary of categories and terms for use in explain prompts.
    If max_examples is None, include every term; otherwise show that many per category plus '...'.
    """
    parts = []
    for category, terms in MUSIC_TAXONOMY.items():
        label = category.capitalize()
        if max_examples is None:
            examples = ", ".join(terms)
        else:
            examples = ", ".join(terms[:max_examples])
            if len(terms) > max_examples:
                examples += ", ..."
        parts.append(f"{label}: {examples}")
    return " | ".join(parts)
