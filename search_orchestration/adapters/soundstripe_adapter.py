from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

# Import your Soundstripe client function
# Adjust this import path to where get_songs actually lives.
from search_orchestration.clients.soundstripe_client import get_songs, get_sound_effects

Selection = Dict[str, List[str]]


def selection_to_get_songs_kwargs(selection: Selection) -> Dict[str, Any]:
    """
    Convert orchestrator selection dict to Soundstripe get_songs kwargs.
    Soundstripe expects comma-separated strings for tags_* fields.
    """
    kwargs: Dict[str, Any] = {}

    if "genre" in selection and selection["genre"]:
        kwargs["tags_genre"] = ",".join(selection["genre"])

    if "instrument" in selection and selection["instrument"]:
        kwargs["tags_instrument"] = ",".join(selection["instrument"])

    if "characteristic" in selection and selection["characteristic"]:
        kwargs["tags_characteristic"] = ",".join(selection["characteristic"])

    if "mood" in selection and selection["mood"]:
        kwargs["tags_mood"] = ",".join(selection["mood"])

    print('kwargs from selection_to_get_songs_kwargs', kwargs)
    return kwargs


def selection_to_get_sfx_kwargs(selection: Selection) -> Dict[str, Any]:
    """
    Convert orchestrator SFX selection dict to Soundstripe get_sound_effects kwargs.

    Soundstripe expects:
      categories="id1,id2,id3"

    Strategy:
    - Prefer the most specific subcategory IDs.
    - If a category has selected subcategories, include ONLY those subcategory IDs.
    - If a category has no selected subcategories, include the parent category ID.
    - Do not include both parent and child IDs together for the same branch.
    - Preserve left-to-right order from the selection object.
    - Global dedupe across all IDs.
    - Limit total IDs to a maximum of 5.
    """
    from search_orchestration.adapters.ai.taxonomy import SFX_TAXONOMY_WITH_IDS

    seen: Set[int] = set()
    ids: List[int] = []
    max_ids = 5

    for category_name, subcategory_names in selection.items():
        if len(ids) >= max_ids:
            break

        category_data = SFX_TAXONOMY_WITH_IDS.get(category_name)
        if not category_data:
            continue

        subcategories = category_data.get("subcategories", {})

        # Normalize/keep only valid subcategories in the original order
        valid_subcategory_ids: List[int] = []
        for subcategory_name in subcategory_names or []:
            subcategory_id = subcategories.get(subcategory_name)
            if subcategory_id is not None and subcategory_id not in seen:
                valid_subcategory_ids.append(subcategory_id)

        if valid_subcategory_ids:
            # Prefer specific subcategories; do NOT include parent ID
            for subcategory_id in valid_subcategory_ids:
                if len(ids) >= max_ids:
                    break
                if subcategory_id not in seen:
                    ids.append(subcategory_id)
                    seen.add(subcategory_id)
        else:
            # No subcategories selected: include the parent category ID
            category_id = category_data.get("id")
            if category_id is not None and category_id not in seen and len(ids) < max_ids:
                ids.append(category_id)
                seen.add(category_id)

    kwargs: Dict[str, Any] = {}
    if ids:
        kwargs["categories"] = ",".join(str(i) for i in ids)

    print("kwargs from selection_to_get_sfx_kwargs", kwargs)
    return kwargs


def soundstripe_search(
    selection: Selection,
    *,
    q: Optional[str] = None,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Calls Soundstripe get_songs() and returns a list of flattened song dicts.

    - `q` can be used to pass the user's free-text query to Soundstripe too
      (optional, but often improves recall).
    """
    kwargs = selection_to_get_songs_kwargs(selection)

    # Optional free-text query (search terms from tag-based search)
    if q:
        kwargs["q"] = q.strip()

    # Your get_songs hardcodes page[size]=100 internally.
    # If you later add paging, this adapter is where you'll pass it in.

    resp = get_songs(**kwargs)
    print('resp from soundstripe_search', len(resp["data"]))
    # Your get_songs() returns the response with `data` list of songs, flattened.

    songs = resp.get("data", [])
    if not isinstance(songs, list):
        return []

    return songs


def soundstripe_sfx_search(
    selection: Selection,
    *,
    q: Optional[str] = None,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Calls Soundstripe get_sound_effects() and returns a list of flattened sound effect dicts.
    """
    kwargs = selection_to_get_sfx_kwargs(selection)

    if q:
        kwargs["q"] = q.strip()

    resp = get_sound_effects(**kwargs)
    print('resp from soundstripe_sfx_search', len(resp["data"]))

    sound_effects = resp.get("data", [])
    if not isinstance(sound_effects, list):
        return []

    return resp.get("data", [])
