
# Run
Please cd to src and run `python3 mproxy.py -p port`

# Known problem
CSIL has pyopenssl installed only in python2.7, but my implementation is in python 3. I didn't realize it until about to turn in. There are two ways to resolve it.

1. Run it on a machine with pyopenssl installed for python 3.3+.
2. cd to `scr2` and run `python3 main.py -p port`. I implemented my program without pyopenssl first. It works well (actually stabler) except it sets SNI to the hostname getting from CONNECT command, instead of getting from client hell0o.


## Part 3

## Periscope
1. Send a REST call to path `/api/v2/followers`, with method `POST`. In the request body, the requested user's ID and a coockie are included in a JSON string. See `1328_169.231.16.159_api.periscope.tv:443`

2. Send a REST call to path `/api/v2/getBroadcasts`, with method `POST`. The body JSON contains the `broadcast_ids`. See `1415_169.231.16.159_api.periscope.tv:443`

## Yelp
1. Sand a GET request with searching parameters (e.g. 'Starbucks') encoded in the URL to endpoint `/search`. See `logs/677_169.231.16.159_auto-api.yelp.com:443`

2. Sand a POST request with parameters encoded in the URL to endpoint `/bookmarks/add`. See `logs/719_169.231.16.159_auto-api.yelp.com:443`
