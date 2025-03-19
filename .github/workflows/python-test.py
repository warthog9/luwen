#!/usr/bin/python3

import urllib.request, json
#from pprint import pprint

fedora_tag_query_url = "https://quay.io/api/v1/repository/fedora/fedora/tag/?onlyActiveTags=true"

# Fetch the existing tags, we'll need these
with urllib.request.urlopen( fedora_tag_query_url ) as url:
    jsTags = json.load( url )

#pprint( jsTags )


latest_indexes = [i for i, x in enumerate(jsTags['tags']) if x['name'] == 'latest']

#pprint( latest_indexes )

latest_digests = []

for x in latest_indexes:
    #pprint( jsTags['tags'][ x ] )
    latest_digests.append( jsTags['tags'][ x ]['manifest_digest'] )

manifest_indexes = [i for i, x in enumerate(jsTags['tags']) if x['manifest_digest'] in latest_digests]

#pprint( manifest_indexes )

filtered_indexes = list( set(manifest_indexes) - set(latest_indexes) )

#pprint( filtered_indexes )

latest_numbers = []

for x in filtered_indexes:
    #print( "Latest: {}".format( jsTags['tags'][x]['name'] ) )
    latest_numbers.append( int(jsTags['tags'][x]['name']) )

# ok rawhide, latest and latest number, anything above and one less

#valid versions

#print( "latest_numbers: {}".format(latest_numbers) )

data = []

for x in jsTags['tags']:
    if "-" in x['name'] \
    or \
    x["name"] in ["rawhide", "latest"]:
        continue

    #print( x['name'] )
    #print( x['name'] in latest_numbers )
    if  x['name'] in latest_numbers \
        or \
        all( int(x['name']) >= i or int(x['name']) >= i - 1 for i in latest_numbers):
            #print( x )
            data.append( x )

print( "::set-output name=matrix::{}".format( repr(json.dumps(data)) ) )
