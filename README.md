## Periscope
1. Send a REST call to path `/api/v2/followers`, with method `POST`. In the request body, the requested user's ID and a coockie are included in a JSON string. See `1328_169.231.16.159_api.periscope.tv:443`

2. Send a REST call to path `/api/v2/getBroadcasts`, with method `POST`. The body JSON contains the `broadcast_ids`. See `1415_169.231.16.159_api.periscope.tv:443`

## Yelp
1. Sand a GET request with searching parameters (e.g. 'Starbucks') encoded in the URL to endpoint `/search`. See `logs/677_169.231.16.159_auto-api.yelp.com:443`

2. Sand a POST request with parameters encoded in the URL to endpoint `/bookmarks/add`. See `logs/719_169.231.16.159_auto-api.yelp.com:443`
