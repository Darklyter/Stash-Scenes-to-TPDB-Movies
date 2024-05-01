import requests
import json
from stashapi.stashapp import StashInterface

stash = StashInterface({"host": "192.168.1.200", "port": 9999})

create_missing_studio = True

headers = {
    'Authorization': 'Bearer xxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': 'tpdb-scraper/1.0.0'
}


def main():
    # Identify the 'No TPDB Movie tag for marking scenes with no associated movie
    no_movie_tag = get_no_movie_tag()
    print(f"Tag 'No TPDB Movie' Found as ID#{no_movie_tag}")

    # Get a list of all scenes from Stash without the tag
    scene_query = {"tags": {"value": str(no_movie_tag), "modifier": "EXCLUDES"}, "movies": {"modifier": "IS_NULL"}, "stash_id_endpoint": {"endpoint": "https://theporndb.net/graphql", "modifier": "NOT_NULL"}}

    # Query to do a specific site instead.  Just replace the number at the end with the correct studio id from Stash.  Only use one of these scene_queries
    # ~ scene_query = {"tags": {"value": str(no_movie_tag), "modifier": "EXCLUDES"}, "movies": {"modifier": "IS_NULL"}, "stash_id_endpoint": {"endpoint": "https://theporndb.net/graphql", "modifier": "NOT_NULL"}, "studios": {"value": 568, "modifier": "EQUALS"}}

    scenelist = stash.find_scenes(f=scene_query, filter={"per_page": -1}, fragment="id title stash_ids{endpoint stash_id} studio{name id} tags{id}")

    # Step through scene list and check for matches from TPDB
    for scene in scenelist:
        tpdb_counter = 0
        for tpdb_id in scene['stash_ids']:
            if "theporndb.net" in tpdb_id['endpoint']:
                tpdb_counter = tpdb_counter + 1
        if tpdb_counter != 1:
            print(f"Aborting match due to more than 1 TPDB Stash_ID for '{scene['title']}' (ID#{scene['id']})")
        else:
            print(f"\nChecking TPDB for '{scene['title']}' with Stash_ID: {scene['stash_ids'][0]['stash_id']}")
            for tpdb_id in scene['stash_ids']:
                if "theporndb.net" in tpdb_id['endpoint']:
                    tpdb_stashid = tpdb_id['stash_id']
            if tpdb_stashid:
                tpdb_match = get_tpdb_scene(tpdb_stashid)
                if tpdb_match:
                    movie = check_stash_for_movie(tpdb_match['movies'][0]['id'], tpdb_match['movies'][0])
                    if movie and movie != "Error":
                        scene_update = update_scene(int(movie), scene['id'])
                        if scene_update:
                            print(f"\tScene '{scene['title']}' ({scene['id']}) attached to movie #{movie} successfully")
                    elif movie == "Error":
                        print(f"\tSomething went wrong with movie tagging Scene '{scene['title']}' ({scene['id']}): {movie}")
                else:
                    # Attach "No TPDB Movie" tag to scene
                    tag_result = stash.update_scenes({"ids": [str(scene['id'])], "tag_ids": {"mode": "ADD", "ids": [str(no_movie_tag)]}})
                    if tag_result:
                        print(f"\tScene '{scene['title']}' ({scene['id']}) tagged as 'No TPDB Movie'")


def update_scene(movie, sceneid):
    # Find out what the next scene index should be
    movie_scenes = stash.find_movie(int(movie), fragment="id scenes{id}")
    index_num = len(movie_scenes['scenes']) + 1

    # Update the scene
    result = stash.update_scene({
        "id": sceneid,
        "movies": {
            "movie_id": movie,
            "scene_index": index_num
        }
    })

    return result


def check_stash_for_movie(movie_uuid, movie_def):
    stash_movie = stash.find_movies(f={"url": {"value": movie_uuid, "modifier": "INCLUDES"}})
    if stash_movie:
        return stash_movie[0]['id']
    else:
        # Get the Studio/Site name for the movie
        print(f"\tChecking TPDB for site information for ID#{movie_def['site_id']}")

        tpdb_link = f"https://api.theporndb.net/sites/{movie_def['site_id']}"
        response = requests.get(tpdb_link, headers=headers, timeout=2)
        if response.status_code == 200:
            result = json.loads(response.content)
            result = result['data']
            if result['name']:
                site_name = result['name']
                stash_site = stash.find_studios(f={"name": {"value": site_name, "modifier": "EQUALS"}})
                if stash_site and stash_site[0]['id']:
                    print(f"\tMatched Stash Site: {stash_site[0]['name']} with ID# {stash_site[0]['id']}")
                    movie_studio = stash_site[0]['id']
                else:
                    print(f"\tMatching studio not found in Stash for '{site_name}'")
                    if create_missing_studio:
                        print(f"\tPer `create_missing_studio` flag, creating studio for '{site_name}'")
                        movie_studio = stash.create_studio({"name": site_name})
                        movie_studio = movie_studio['id']
                    else:
                        print(f"\tPer `create_missing_studio` flag, not creating studio for '{site_name}' and using 'Movie Unknown Studio' instead")
                        movie_studio = get_generic_movie_studio()

        else:
            print(f"\tCouldn't find TPDB Site Information for {movie_def['site_id']}")

        if not movie_studio:
            print("\tSomething went wrong matching or creating studio for movie.  Aborting")
            return "Error"

        # Ignore the "default" image for missing images on TPDB
        if "default" in movie_def['background']['full'] and "png" in movie_def['background']['full']:
            movie_def['background']['full'] = None

        if "default" in movie_def['background_back']['full'] and "png" in movie_def['background_back']['full']:
            movie_def['background_back']['full'] = None

        # We need to check for an existing movie with the same title, since Stash uses the name as a unique constraint
        movie_temp = stash.find_movies(f={"name": {"value": movie_def['title'], "modifier": "EQUALS"}})
        if movie_temp:
            # If we already have one, append the studio id formatted like "This Great Movie (567)"
            movie_def['title'] = f"{movie_def['title']} ({movie_studio})"

        # And then create a new movie instance from TPDB data
        print(f"\tCreating new movie entry for '{movie_def['title']}' with studio '{movie_studio}'")
        movie_id = stash.create_movie({
            "name": movie_def['title'],
            "duration": movie_def['duration'],
            "date": movie_def['date'],
            "studio_id": movie_studio,
            "synopsis": movie_def['description'],
            "url": f"https://theporndb.net/movies/{movie_uuid}",
            "front_image": movie_def['background']['full'],
            "back_image": movie_def['background_back']['full']
        })

        return movie_id['id']


def get_tpdb_scene(stash_id):
    tpdb_link = f"https://api.theporndb.net/scenes/{stash_id}"
    response = requests.get(tpdb_link, headers=headers, timeout=2)
    if response.status_code == 200:
        result = json.loads(response.content)
        result = result['data']
        if result['movies']:
            print(f"\tFound a scene movie attached for Stash_ID: {stash_id}")
            return result
        else:
            print(f"\tNo Movies found for Stash_ID: {stash_id}")
            return None
    else:
        print(response)
        return None


def get_no_movie_tag():
    no_movie_tag = stash.find_tag("No TPDB Movie", fragment="id", create=True)

    if not no_movie_tag:
        print("Could neither find nor create 'No TPDB Movie' tag.  Aborting...'")
        return False

    return no_movie_tag['id']


def get_generic_movie_studio():
    movie_studio = stash.find_studio("Movie Unknown Studio", fragment="id", create=True)

    if not movie_studio:
        print("Could neither find nor create 'Movie Unknown Studio' tag.  Aborting...'")
        return False

    return movie_studio['id']


if __name__ == "__main__":
    main()
