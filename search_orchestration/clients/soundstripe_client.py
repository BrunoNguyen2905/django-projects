# Soundstripe API Client
# https://docs.soundstripe.com/docs/integrating-soundstripes-content-into-your-application#option-1-recommended-index-soundstripes-api-nightly

from typing import Dict, List, Optional, Any
from cache_memoize import cache_memoize

import httpx
from environs import Env

env = Env()
env.read_env()

# api_key = env.str("SOUNDSTRIPE_API_KEY")
api_key = env.str("SOUNDSTRIPE_API_KEY_DEVELOPMENT")

api_base = "https://api.soundstripe.com/v1"


def _get_headers() -> Dict[str, str]:
    """Get common headers for API requests."""
    return {
        "accept": "application/json",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
        "Authorization": f"Token {api_key}"
    }


def _cache_hit(*args, **kwargs):
    print('SS client cachehit')


@cache_memoize(3600, hit_callable=_cache_hit)
def _make_request(method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an HTTP request to the Soundstripe API."""
    url = f"{api_base}/{endpoint}"
    headers = _get_headers()

    if method.lower() == "get":
        response = httpx.get(url, headers=headers, params=params or {})
        if response.status_code == 200:
            return response.json()
        else:
            raise httpx.HTTPError(
                f"HTTP {response.status_code}: {response.text}")
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")


def get_songs(
    bpm_max: Optional[int] = None,
    bpm_min: Optional[int] = None,
    duration_consider_alternate_audio_files: Optional[bool] = None,
    duration_max: Optional[int] = None,
    duration_min: Optional[int] = None,
    energy: Optional[str] = None,
    include_alternate_audio_files: Optional[bool] = None,
    instrumental: Optional[bool] = None,
    q: Optional[str] = None,
    tags_characteristic: Optional[str] = None,
    tags_genre: Optional[str] = None,
    tags_instrument: Optional[str] = None,
    tags_mood: Optional[str] = None,
    vocals: Optional[bool] = None,
    mode: Optional[str] = None,
    key: Optional[str] = None
) -> Dict:
    """
    Retrieve a list of songs from the Soundstripe API.

    Args:
        bpm_max: Maximum BPM
        bpm_min: Minimum BPM
        duration_consider_alternate_audio_files: If true, songs will be returned if any of their audio files match the supplied duration criteria
        duration_max: Maximum duration of the song's primary audio file
        duration_min: Minimum duration of the song's primary audio file
        energy: Energy to filter by. One of: very_low, low, medium or high
        include_alternate_audio_files: If true, all audio files for each song will be returned
        instrumental: If true, only show songs that have at least one instrumental audio file
        q: Search query
        tags_characteristic: Comma-separated characteristic tags to filter by
        tags_genre: Comma-separated genre tags to filter by
        tags_instrument: Comma-separated instrument tags to filter by
        tags_mood: Comma-separated mood tags to filter by
        vocals: If true, only show songs that have at least one vocal audio file
        mode: Mode to filter by (e.g., major, minor)
        key: Key to filter by (e.g., C, D, E)

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}

    if bpm_max is not None:
        params["filter[bpm][max]"] = bpm_max
    if bpm_min is not None:
        params["filter[bpm][min]"] = bpm_min
    if duration_consider_alternate_audio_files is not None:
        params["filter[duration][consider_alternate_audio_files]"] = duration_consider_alternate_audio_files
    if duration_max is not None:
        params["filter[duration][max]"] = duration_max
    if duration_min is not None:
        params["filter[duration][min]"] = duration_min
    if energy is not None:
        params["filter[energy]"] = energy
    if include_alternate_audio_files is not None:
        params["filter[include_alternate_audio_files]"] = include_alternate_audio_files
    if instrumental is not None:
        params["filter[instrumental]"] = instrumental
    if q is not None:
        params["filter[q]"] = q
    if tags_characteristic is not None:
        params["filter[tags][characteristic]"] = tags_characteristic
    if tags_genre is not None:
        params["filter[tags][genre]"] = tags_genre
    if tags_instrument is not None:
        params["filter[tags][instrument]"] = tags_instrument
    if tags_mood is not None:
        params["filter[tags][mood]"] = tags_mood
    if vocals is not None:
        params["filter[vocals]"] = vocals
    if mode is not None:
        params["filter[key][mode]"] = mode
    if key is not None:
        params["filter[key][name]"] = key
    params["page[size]"] = 100  # TODO static search for 100
    print('params from get_songs', params)
    # TODO page[number] = page_num
    response = _make_request("GET", "songs", params)
    #  if no data, return empty list
    if not response.get("data", []):
        print('no data from get_songs', response)
        return response

    # If there's no included data, it might mean no results found
    if "included" not in response or not response["included"]:
        # Return response with empty data if no included data (no results)
        response["data"] = response.get("data", [])
        return response
    # Create lookup dictionaries for artists and audio_files
    artists_lookup = {}
    audio_files_lookup = {}

    for item in response["included"]:
        if item["type"] == "artists":
            # Flatten artist data by removing type and moving attributes to top level
            artist_data = {"id": item["id"]}
            if "attributes" in item:
                artist_data.update(item["attributes"])
            artists_lookup[item["id"]] = artist_data
        elif item["type"] == "audio_files":
            # Flatten audio file data by removing type and moving attributes to top level
            audio_file_data = {"id": item["id"]}
            if "attributes" in item:
                audio_file_data.update(item["attributes"])
            audio_files_lookup[item["id"]] = audio_file_data

    # Process each song in the data array
    for song in response["data"]:
        # Add static type field - overridden for frontend consistency across catalogs
        song["type"] = "song"

        # Flatten attributes to top level
        if "attributes" in song:
            song.update(song["attributes"])
            del song["attributes"]

        # Inline artist data
        if "relationships" in song and "artists" in song["relationships"]:
            artist_data = []
            for artist_ref in song["relationships"]["artists"]["data"]:
                artist_id = artist_ref["id"]
                if artist_id in artists_lookup:
                    artist_data.append(artists_lookup[artist_id])
            song["artists"] = artist_data

        # Inline audio files data
        if "relationships" in song and "audio_files" in song["relationships"]:
            audio_files_data = []
            for audio_file_ref in song["relationships"]["audio_files"]["data"]:
                audio_file_id = audio_file_ref["id"]
                if audio_file_id in audio_files_lookup:
                    audio_files_data.append(audio_files_lookup[audio_file_id])
            song["audio_files"] = audio_files_data

        # Add primary_audio field derived from the first audio file in relationships
        if "audio_files" in song and len(song["audio_files"]) > 0:
            # The first audio file listed is the primary audio file
            primary_audio_file = song["audio_files"][0]

            if "versions" in primary_audio_file:
                song["primary_audio"] = {}
                if "mp3" in primary_audio_file["versions"]:
                    song["primary_audio"]["mp3"] = primary_audio_file["versions"]["mp3"]
                if "wav" in primary_audio_file["versions"]:
                    song["primary_audio"]["wav"] = primary_audio_file["versions"]["wav"]
                # Add duration from the primary audio file
                if "duration" in primary_audio_file:
                    song["primary_audio"]["duration_s"] = int(
                        round(primary_audio_file["duration"]))

        # Remove relationships key after it has been processed
        if "relationships" in song:
            del song["relationships"]

    # Remove the included key from the response
    del response["included"]

    return response


def get_song(song_id: str) -> Dict:
    """
    Retrieve a single song by ID.

    Args:
        song_id: The ID of the song to retrieve

    Returns:
        Dict: The song data
    """
    response = _make_request("GET", f"songs/{song_id}")

    # If there's no included data, raise an exception
    if "included" not in response or not response["included"]:
        raise Exception(
            "Soundstripe API did not return expected format: missing 'included' data")

    # Create lookup dictionaries for artists and audio_files
    artists_lookup = {}
    audio_files_lookup = {}

    for item in response["included"]:
        if item["type"] == "artists":
            # Flatten artist data by removing type and moving attributes to top level
            artist_data = {"id": item["id"]}
            if "attributes" in item:
                artist_data.update(item["attributes"])
            artists_lookup[item["id"]] = artist_data
        elif item["type"] == "audio_files":
            # Flatten audio file data by removing type and moving attributes to top level
            audio_file_data = {"id": item["id"]}
            if "attributes" in item:
                audio_file_data.update(item["attributes"])
            audio_files_lookup[item["id"]] = audio_file_data

    # Process the song data
    song = response["data"]

    # Add static type field - overridden for frontend consistency across catalogs
    song["type"] = "song"

    # Flatten attributes to top level
    if "attributes" in song:
        song.update(song["attributes"])
        del song["attributes"]

    # Inline artist data
    if "relationships" in song and "artists" in song["relationships"]:
        artist_data = []
        for artist_ref in song["relationships"]["artists"]["data"]:
            artist_id = artist_ref["id"]
            if artist_id in artists_lookup:
                artist_data.append(artists_lookup[artist_id])
        song["artists"] = artist_data

    # Inline audio files data
    if "relationships" in song and "audio_files" in song["relationships"]:
        audio_files_data = []
        for audio_file_ref in song["relationships"]["audio_files"]["data"]:
            audio_file_id = audio_file_ref["id"]
            if audio_file_id in audio_files_lookup:
                audio_files_data.append(audio_files_lookup[audio_file_id])
        song["audio_files"] = audio_files_data

    # Add primary_audio field derived from the first audio file in relationships
    if "audio_files" in song and len(song["audio_files"]) > 0:
        # The first audio file listed is the primary audio file
        primary_audio_file = song["audio_files"][0]

        if "versions" in primary_audio_file:
            song["primary_audio"] = {}
            if "mp3" in primary_audio_file["versions"]:
                song["primary_audio"]["mp3"] = primary_audio_file["versions"]["mp3"]
            if "wav" in primary_audio_file["versions"]:
                song["primary_audio"]["wav"] = primary_audio_file["versions"]["wav"]
            # Add duration from the primary audio file
            if "duration" in primary_audio_file:
                song["primary_audio"]["duration_s"] = int(
                    round(primary_audio_file["duration"]))

    # Remove relationships key after it has been processed
    if "relationships" in song:
        del song["relationships"]

    # Remove the included key from the response
    del response["included"]

    # Remove links key and return just the data
    if "links" in song:
        del song["links"]

    return song


def get_tags(category: Optional[str] = None, size: Optional[int] = None, page: Optional[int] = None) -> Dict:
    """
    Retrieve a list of tags from the Soundstripe API.

    Args:
        category: Category of tags to filter by. One of: characteristic, genre, instrument, or mood.
        size: Number of items per page (default: 10)
        page: Page number to retrieve (default: 1)

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}
    if category is not None:
        valid_categories = ["characteristic", "genre", "instrument", "mood"]
        if category not in valid_categories:
            raise ValueError(
                f"Tag category must be one of: {', '.join(valid_categories)}")
        params["filter[category]"] = category
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page

    return _make_request("GET", "tags", params)


def get_sound_effects(
    q: Optional[str] = None,
    categories: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None
) -> Dict:
    """
    Retrieve a list of sound effects from the Soundstripe API. Production API Key required.

    Args:
        q: Search query
        categories: Comma-separated categories to filter by. Category IDs or names can be used
                   interchangeably to filter. If a category ID or name is prefixed with a hyphen (-),
                   sound effects in that category will be filtered out.
        size: Number of items per page (default: 10, range: 1-100)
        page: Page number to retrieve (default: 1)

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}

    if q is not None:
        params["filter[q]"] = q
    if categories is not None:
        params["filter[categories]"] = categories
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page

    params["page[size]"] = 100  # TODO static page size

    response = _make_request("GET", "sound_effects", params)

    # Flatten attributes to top level for each sound effect
    if "data" in response:
        for sound_effect in response["data"]:
            # Add static type field - overridden for frontend consistency across catalogs
            sound_effect["type"] = "sfx"

            if "attributes" in sound_effect:
                sound_effect.update(sound_effect["attributes"])
                del sound_effect["attributes"]

            # Add all_categories field combining categories and subcategories
            categories_list = sound_effect.get("categories", [])
            subcategories_list = sound_effect.get("subcategories", [])
            sound_effect["all_categories"] = categories_list + \
                subcategories_list

            # Add primary_audio from versions
            if "versions" in sound_effect:
                sound_effect["primary_audio"] = {}
                versions = sound_effect["versions"]
                if "mp3" in versions:
                    sound_effect["primary_audio"]["mp3"] = versions["mp3"]
                if "wav" in versions:
                    sound_effect["primary_audio"]["wav"] = versions["wav"]

            # Add duration to primary_audio from the top-level duration field
            if "duration" in sound_effect:
                if "primary_audio" not in sound_effect:
                    sound_effect["primary_audio"] = {}
                sound_effect["primary_audio"]["duration_s"] = int(
                    round(sound_effect["duration"]))

    return response


def get_sound_effect(sfx_id: str) -> Dict:
    """
    Retrieve a single sound effect by ID.

    Args:
        sfx_id: The ID of the sound effect to retrieve

    Returns:
        Dict: The sound effect data as a flat dictionary
    """
    response = _make_request("GET", f"sound_effects/{sfx_id}")

    # Get the sound effect data
    sound_effect = response.get("data", {})

    # Add static type field - overridden for frontend consistency across catalogs
    sound_effect["type"] = "sfx"

    # Flatten attributes to top level
    if "attributes" in sound_effect:
        sound_effect.update(sound_effect["attributes"])
        del sound_effect["attributes"]

    # Add all_categories field combining categories and subcategories
    categories_list = sound_effect.get("categories", [])
    subcategories_list = sound_effect.get("subcategories", [])
    sound_effect["all_categories"] = categories_list + subcategories_list

    # Add primary_audio from versions
    if "versions" in sound_effect:
        sound_effect["primary_audio"] = {}
        versions = sound_effect["versions"]
        if "mp3" in versions:
            sound_effect["primary_audio"]["mp3"] = versions["mp3"]
        if "wav" in versions:
            sound_effect["primary_audio"]["wav"] = versions["wav"]

    # Add duration to primary_audio from the top-level duration field
    if "duration" in sound_effect:
        if "primary_audio" not in sound_effect:
            sound_effect["primary_audio"] = {}
        sound_effect["primary_audio"]["duration_s"] = int(
            round(sound_effect["duration"]))

    # Remove links if present
    if "links" in sound_effect:
        del sound_effect["links"]

    return sound_effect


def get_categories(include: Optional[List[str]] = None, size: Optional[int] = None, page: Optional[int] = None) -> Dict:
    """
    Retrieve a list of SFX categories from the Soundstripe API.

    Args:
        include: List of related resources to include.
                Valid options: subcategories
        size: Number of items per page (default: 10)
        page: Page number to retrieve (default: 1)

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}
    if include is not None:
        params["include"] = include
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page

    return _make_request("GET", "categories", params)


def get_category(category_id: str, include: Optional[str] = None) -> Dict:
    """
    Retrieve a category by ID from the Soundstripe API.

    Args:
        category_id: The ID of the category to retrieve
        include: Comma-separated string of related resources to include.
                Valid options: subcategories

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}
    if include is not None:
        params["include"] = include

    return _make_request("GET", f"categories/{category_id}", params)


def get_playlists(
    include: Optional[str] = None,
    include_alternate_audio_files: Optional[bool] = None,
    playlist_category_ids: Optional[str] = None,
    media_type: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None
) -> Dict:
    """
    Retrieve a list of playlists from the Soundstripe API.

    When passed with an includes parameter, it can return songs from the playlist
    along with their primary and alternate audio files. Only the first page of
    songs and audio files will be returned but remaining pages can be retrieved
    via the v1/playlists/:id endpoint.

    Args:
        include: Returns related resources of the playlist. Must be a comma separated
                string consisting of one or many: songs, songs.audio_files, songs.artists,
                playlist_categories. For more information on include see the JSON:API spec.
        include_alternate_audio_files: If true, all audio files for each song will be
                returned in the audio_files relationship, and in the top-level included key.
                If false, only primary audio files will be returned. By default, this is false.
        playlist_category_ids: Filter playlists by category. Must be a comma separated string of IDs.
        media_type: Filters playlists by media type. Can be either songs or sound_effects. Defaults to songs.
        size: The number of Playlists to return from 1-100. Defaults to 10.
        page: The desired page number, one-indexed. Defaults to 1.

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}

    if include is not None:
        params["include"] = include
    if include_alternate_audio_files is not None:
        params["filter[include_alternate_audio_files]"] = include_alternate_audio_files
    if playlist_category_ids is not None:
        params["filter[playlist_category_ids]"] = playlist_category_ids
    if media_type is not None:
        params["filter[media_type]"] = media_type
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page

    resp = _make_request("GET", "playlists", params)

    # TODO count total songs and include in return value
    # song_count = resp["data"]["relationships"]["songs"]["data"]
    # resp["data"]["song_count"] = len(resp["data"]["relationships"]["songs"]["data"])

    return resp


def get_playlist(
    playlist_id: str,
    include: Optional[str] = None,
    include_alternate_audio_files: Optional[bool] = None,
    size: Optional[int] = None,
    page: Optional[int] = None,
    media_type: Optional[str] = None
) -> Dict:
    """
    This endpoint retrieves a playlist. When passed with an includes parameter,
    it can return songs from the playlist along with their primary and alternate audio files.

    Args:
        playlist_id: The playlist's ID (required)
        include: Returns related resources of the playlist. Must be a comma separated
                string consisting of one or many: songs, songs.audio_files, songs.artists,
                playlist_categories. For more information on include see the JSON:API spec.
        include_alternate_audio_files: If true, all audio files for each song will be
                returned in the audio_files relationship, and in the top-level included key.
                If false, only primary audio files will be returned. By default, this is false.
        size: The number of songs or sound effects to be returned for the given playlist. Defaults to 10.
        page: Specify the page to retrieve when including songs via the include parameter. Defaults to 1.
        media_type: Returns playlist of that media type. Value can only be songs or sound_effects
                   and defaults to songs if not passed.

    Returns:
        Dict: The API response data
    """
    # Build query parameters
    params = {}

    if include is not None:
        params["include"] = include
    if include_alternate_audio_files is not None:
        params["filter[include_alternate_audio_files]"] = include_alternate_audio_files
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page
    if media_type is not None:
        params["filter[media_type]"] = media_type

    return _make_request("GET", f"playlists/{playlist_id}", params)


def get_playlist_categories(size: Optional[int] = None, page: Optional[int] = None) -> Dict:
    """
    Retrieve a list of playlist categories from the Soundstripe API.

    Args:
        size: Number of items per page (default: 10, range: 1-100)
        page: Page number to retrieve (default: 1)

    Returns:
        Dict: The API response data with {<id>: <attributes["name"]>} format
    """
    # Build query parameters
    params = {}
    if size is not None:
        params["page[size]"] = size
    if page is not None:
        params["page[number]"] = page

    response = _make_request("GET", "playlist_categories", params)

    # Transform the response to collect all results into a dict {<id>: <attributes["name"]>}
    result = {}
    if "data" in response:
        for item in response["data"]:
            if "id" in item and "attributes" in item and "name" in item["attributes"]:
                result[item["id"]] = item["attributes"]["name"]

    return result


def get_playlist_category(playlist_category_id: str) -> Dict:
    """
    Retrieve a playlist category by ID from the Soundstripe API.

    Args:
        playlist_category_id: The ID of the playlist category to retrieve

    Returns:
        Dict: The API response data
    """
    return _make_request("GET", f"playlist_categories/{playlist_category_id}")
