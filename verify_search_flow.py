#!/usr/bin/env python3
"""
Verification script for the complete music search flow:
User input → LLM taxonomy selection → Soundstripe API queries → Results

Usage: python verify_search_flow.py "uplifting cinematic piano build"
"""

import sys
import json
from typing import Dict, List, Any, Optional

# Django setup for settings access
import django
from django.conf import settings

# Load environment variables first
import os
from environs import Env
env = Env()
env.read_env()

# Configure Django settings
if not settings.configured:
    settings.configure(
        OPENAI_API_KEY=env.str("OPENAI_API_KEY", ""),
        SOUNDSTRIPE_API_KEY_DEVELOPMENT=env.str("SOUNDSTRIPE_API_KEY_DEVELOPMENT", ""),
        SECRET_KEY=env.str("SECRET_KEY", "test-key"),
        INSTALLED_APPS=['django.contrib.contenttypes'],
        USE_TZ=True,
    )
    django.setup()

# Import our search components
from search_orchestration.adapters.ai.llm_search_orchestrator import (
    orchestrate_search,
    generate_search_selections_llm,
    validate_and_normalize_selections
)
from search_orchestration.adapters.soundstripe_adapter import soundstripe_search


def test_llm_only(user_query: str):
    """Test only the LLM taxonomy generation without API calls."""
    print(f"🧠 Testing LLM taxonomy generation for: \"{user_query}\"")

    try:
        # Test LLM generation directly
        from search_orchestration.adapters.ai.llm_search_orchestrator import build_prompt

        prompt = build_prompt(user_query, broaden=False, prior_counts=None)
        print(f"📝 Generated prompt ({len(prompt)} chars)")

        raw_selections = generate_search_selections_llm(prompt, expected_count=5)
        print(f"🤖 LLM generated {len(raw_selections)} raw selections")

        if raw_selections:
            validated_selections = validate_and_normalize_selections(raw_selections, expected_count=5)
            print(f"✅ Validation successful: {len(validated_selections)} selections")

            print("\n🏷️  Generated Selections:")
            for i, sel in enumerate(validated_selections, 1):
                terms = []
                for category, values in sel.items():
                    if values:
                        terms.extend([f"{category}:{v}" for v in values])
                print(f"   {i}. {' | '.join(terms) if terms else 'Empty selection'}")

            print("\n✅ LLM taxonomy generation working correctly!")
            return True
        else:
            print("❌ LLM returned no selections")
            return False

    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False


def print_raw_data(raw_llm_outputs: List[Dict], raw_api_responses: List[Dict]):
    """Print raw LLM outputs and API responses for debugging."""
    print(f"\n🔄 SEARCH PROCESS SUMMARY:")
    print(f"   • Rounds Completed: {len(raw_llm_outputs)}")
    print(f"   • Total Selections Generated: {sum(len(output['raw_output']) for output in raw_llm_outputs)}")
    print(f"   • API Calls Made: {len(raw_api_responses)}")
    print(f"   • Total Songs Found: {sum(response['data_count'] for response in raw_api_responses)}")

    # Group API responses by round
    api_by_round = {}
    for response in raw_api_responses:
        round_num = response['round']
        if round_num not in api_by_round:
            api_by_round[round_num] = []
        api_by_round[round_num].append(response)

    if raw_llm_outputs:
        print(f"\n🤖 ROUND-BY-ROUND BREAKDOWN:")
        for i, output in enumerate(raw_llm_outputs, 1):
            round_api = api_by_round.get(i, [])
            round_songs = sum(r['data_count'] for r in round_api)

            print(f"  Round {i}:")
            print(f"    🤖 LLM: Generated {len(output['raw_output'])} selections (this round only, no accumulation)")
            print(f"    📡 API: 1 call with merged selection → {round_songs} songs found")
            print(f"    📋 Individual selections: {output['raw_output']}")
            if round_api:
                merged_sel = round_api[0]['selection'] if round_api else {}
                print(f"    🔀 Merged selection sent to get_songs: {merged_sel}")
                print(f"    📊 API Result: {round_api[0]['data_count']} songs")
            print()


def display_results(
    results: List[Dict[str, Any]],
    selections_used: Dict[str, List[str]],
    debug_info: Dict[str, Any],
):
    """Display search results in a readable format. selections_used is a merged dict {category: [terms]}."""
    print("\n" + "="*80)
    print("🎵 MUSIC SEARCH RESULTS")
    print("="*80)

    print(f"\n📊 Search Summary:")
    print(f"   • Total songs found: {len(results)}")
    print(f"   • Filter categories: {len(selections_used)}")

    if results:
        print(f"\n🎼 Top {min(5, len(results))} Results:")

        for i, song in enumerate(results[:5], 1):
            print(f"\n   {i}. {song.get('title', 'Unknown Title')}")
            print(f"      Artist: {song.get('artist_name', 'Unknown Artist')}")
            print(f"      Genre: {song.get('genre', 'N/A')}")
            print(f"      BPM: {song.get('bpm', 'N/A')}")
            print(f"      Duration: {song.get('duration', 'N/A')}s")
            if song.get('audio_files'):
                audio_file = song['audio_files'][0] if isinstance(song['audio_files'], list) else song['audio_files']
                print(f"      Preview: {audio_file.get('preview_url', 'N/A')}")

    if selections_used:
        print(f"\n🏷️  Selections Used (merged):")
        for category, values in selections_used.items():
            if values:
                print(f"   • {category}: {', '.join(values)}")

    if debug_info and isinstance(debug_info, list):
        print(f"\n🔍 Debug Info:")
        for round_info in debug_info:
            if 'round' in round_info:
                print(f"   Round {round_info['round']}: Generated {round_info.get('selections_generated', 0)} selections, "
                      f"Valid: {round_info.get('valid_selections', 0)}, Total so far: {round_info.get('total_selections_so_far', 0)}")
            elif 'phase' in round_info:
                print(f"   {round_info['phase'].title()}: {round_info.get('total_selections_used', 0)} selections used, "
                      f"{round_info.get('total_results_found', 0)} results found, "
                      f"Target {round_info.get('min_results_target', 0)} {'✓' if round_info.get('target_achieved', False) else '✗'}")

    print("\n" + "="*80)


def main():
    """Main verification function."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python verify_search_flow.py \"your music description\" [--dry-run]")
        print()
        print("Examples:")
        print("  python verify_search_flow.py \"uplifting cinematic piano build\"")
        print("  python verify_search_flow.py \"uplifting cinematic piano build\" --dry-run")
        print()
        print("Options:")
        print("  --dry-run    Test only LLM taxonomy generation (no API calls)")
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv
    user_query = sys.argv[1] if len(sys.argv) == 2 else sys.argv[1]

    user_query = sys.argv[1]

    # Check for required API keys (only OpenAI needed for dry run)
    openai_key = getattr(settings, 'OPENAI_API_KEY', '')

    if not openai_key or openai_key.startswith('your-'):
        print("❌ Error: OpenAI API key not configured properly in .env file")
        print("   Make sure OPENAI_API_KEY is set in your .env file")
        sys.exit(1)

    if dry_run:
        print("🔍 DRY RUN MODE - Testing LLM taxonomy generation only")
        print("   (No Soundstripe API calls will be made)")
        print()

        success = test_llm_only(user_query)
        if success:
            print("\n🎉 Dry run successful! LLM taxonomy generation is working.")
            print("   Run without --dry-run to test the full flow with Soundstripe API.")
        return

    # Full run needs both API keys
    soundstripe_key = getattr(settings, 'SOUNDSTRIPE_API_KEY_DEVELOPMENT', '')
    if not soundstripe_key or soundstripe_key.startswith('your-'):
        print("❌ Error: Soundstripe API key not configured properly in .env file")
        print("   Make sure SOUNDSTRIPE_API_KEY_DEVELOPMENT is set in your .env file")
        sys.exit(1)

    print(f"🎵 Testing music search flow with query: \"{user_query}\"")
    print("🤖 Step 1: LLM generates taxonomy selections...")
    print("🔍 Step 2: Querying Soundstripe API...")
    print("📊 Step 3: Processing and displaying results...\n")

    # Create wrapper functions to capture raw outputs
    raw_llm_outputs = []
    raw_api_responses = []
    current_round = 0

    def llm_generate_with_logging(prompt: str, expected_count: int = 5):
        """Wrapper to capture raw LLM output."""
        nonlocal current_round
        from search_orchestration.adapters.ai.llm_search_orchestrator import generate_search_selections_llm
        result = generate_search_selections_llm(prompt, expected_count)
        current_round += 1
        raw_llm_outputs.append({
            'round': current_round,
            'prompt': prompt[:200] + '...' if len(prompt) > 200 else prompt,
            'expected_count': expected_count,
            'raw_output': result
        })
        print(f"🤖 Round {current_round}: LLM generated {len(result)} selections")
        return result

    def soundstripe_search_with_logging(selection, q=None):
        """Wrapper to capture raw API responses."""
        result = soundstripe_search(selection, q=q)

        # Log raw response structure
        if isinstance(result, list):
            response_info = f"List with {len(result)} items"
            data_count = len(result)
        elif isinstance(result, dict):
            response_info = f"Dict with keys: {list(result.keys())}"
            data_count = len(result.get('data', []))
        else:
            response_info = f"Type: {type(result)}"
            data_count = 0

        raw_api_responses.append({
            'round': current_round,
            'selection': selection,
            'query': q,
            'response_structure': response_info,
            'data_count': data_count,
            'raw_sample': str(result)[:200] + '...' if len(str(result)) > 200 else str(result)
        })

        # Only log once per round for merged selections
        if not hasattr(soundstripe_search_with_logging, '_logged_rounds'):
            soundstripe_search_with_logging._logged_rounds = set()

        if current_round not in soundstripe_search_with_logging._logged_rounds:
            soundstripe_search_with_logging._logged_rounds.add(current_round)
            print(f"📡 Round {current_round} API: Single call with merged selection → {data_count} songs")
        else:
            print(f"📊 Round {current_round} result: {data_count} songs")
        return result

    try:
        # Run the complete search flow
        results, selections_used, debug = orchestrate_search(
            user_text=user_query,
            soundstripe_search=soundstripe_search_with_logging,
            llm_generate_json=llm_generate_with_logging,
            min_results=5,
            max_rounds=3
        )

        # Display results
        display_results(results, selections_used, debug.rounds if hasattr(debug, 'rounds') else [])

        # Display raw data
        print_raw_data(raw_llm_outputs, raw_api_responses)

        # Summary
        if results:
            print("\n✅ Search flow completed successfully!")
        else:
            print("\n⚠️  No results found - this could be due to:")
            print("   • API rate limits")
            print("   • No matching songs in the database")
            print("   • Network connectivity issues")
            print("   • Check the selections used above for relevance")

    except ValueError as e:
        if "LLM output must contain exactly" in str(e):
            print(f"\n❌ LLM Error: {e}")
            print("   The LLM didn't generate the expected 5 selections.")
            print("   This might be due to:")
            print("   • OpenAI API key issues")
            print("   • Model rate limits")
            print("   • Invalid taxonomy terms in the prompt")
            print("   • Try again or check your OpenAI account status")
        else:
            print(f"\n❌ Validation Error: {e}")
        sys.exit(1)

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Error during search: {error_msg}")

        if "401" in error_msg or "API key" in error_msg.lower():
            print("   This appears to be an API authentication error.")
            print("   Check your .env file for correct API keys.")
        elif "missing 'included' data" in error_msg:
            print("   Soundstripe API returned unexpected format.")
            print("   This might mean:")
            print("   • No results found for the query")
            print("   • API key issues")
            print("   • API response format changed")
            print("   • The selections might be working, but no matching songs exist")
        elif "LLM" in error_msg:
            print("   This appears to be an LLM/OpenAI API error.")
            print("   Check your OpenAI API key and account status.")

        print("\n🔧 Troubleshooting tips:")
        print("   1. Verify API keys in .env file")
        print("   2. Check OpenAI account has credits")
        print("   3. Test with simpler queries")
        print("   4. Check network connectivity")

        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()