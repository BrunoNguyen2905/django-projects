from __future__ import annotations

from typing import Any, Dict, List, Optional

# Import your Soundstripe client function
# Adjust this import path to where get_songs actually lives.
from search_orchestration.clients.soundstripe_client import get_songs

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

    # Optional free-text query
    # if q:
    #     kwargs["q"] = q

    # Your get_songs hardcodes page[size]=20 internally.
    # If you later add paging, this adapter is where you'll pass it in.

    resp = get_songs(**kwargs)
    print('resp from soundstripe_search', len(resp["data"]))
    # Your get_songs() returns the response with `data` list of songs, flattened.
    songs = resp.get("data", [])
    if not isinstance(songs, list):
        return []

    return songs