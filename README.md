# Stash-Scenes-to-TPDB-Movies

This is a simple script to go through your Stash scenes and try to find any that have attached movies on TPDB.

The scenes must already be matched/scraped to current TPDB entries on the "api.theporndb.net" Stash endpoint, since it uses the UUID/Stash_ID to perform the match.  Please realize that TPDB only has about 20k movies with attached scenes currently (out of about 300k total movies)

The script will auto-create a movie if it hasn't already seen the entry, even if the movie already exists in your Stash.  The reason for this is that I use the Movie's URL field to hold the TPDB UUID for matching.  (I can't query against the Alias field in GQL or else I would probably use that)  Because of that the url attached to the movie will be a link to the TPDB movie page, instead of the "real" page on the studio or distributor website.

It will create a generic "Unknown Movie Studio" studio in Stash on the first run.  If it can't find a match for the TPDB movie studio in your Stash database it will assign the movie to this generic one.  You can go back and clean it up as you would like.  I didn't have it auto-create the studio because, very bluntly, I didn't want it creating a bunch of slightly off variations in my Studios table.

It will also create a "No TPDB Movie" tag, which will be assigned to any scene that TPDB doesn't have listed as a member of a movie.  The first time you run the script it will take forever depending on the size of your collection, but will ignore this tag (or any scenes with movies already attached) so future runs should go more quickly.

Stashtools is required, which you can install with "pip install stashapp-tools"

By default it will run through your entire collection, but if you'd like to do a studio at a time you can comment line 22, uncomment line 25 and change the studio id to whatever you would like.  The one currently in there (1126) is HotWifeXXX in my Stash, for example.

Also as a side note, if something goes screwy you can always just delete the created movie.  That will remove them from the attached scenes, but won't mess with the scenes apart from that.  But I would back up your database before you run this thing, just in case.  For all I know this thing will set your house on fire and get your dog pregnant.  /shrug
