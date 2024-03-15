import requests
import urllib.parse
import os
import datetime
from flask import Flask, redirect, request, jsonify, session, render_template



app = Flask(__name__)
app.secret_key = '53d355f8-571a-4590-a310-1f9579440851'

#spotify web api info
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
#REDIRECT_URI = "http://10.18.51.200:5000/callback"
REDIRECT_URI = "http://127.0.0.1:5000/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/"
#ticketmaster info
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
TICKETMASTER_API_SECRET = os.getenv("TICKETMASTER_API_SECRET")
TICKETMASTER_API_BASE_URL = "https://app.ticketmaster.com/discovery/v2/"
#nominatim
NOMINATIM_API_BASE_URL = "https://nominatim.openstreetmap.org/search"


@app.route('/')
def index():
    print(os.getcwd())
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # scope = 'user-read-private user-read-email'
    scope = 'user-read-private user-read-email user-top-read'

    if request.method == "POST":
        location = request.form['location']
        city, state = map(str.strip, location.split(','))
        session['city'] = city
        session['state'] = state
        print(session['city'])
        print(session['state'])

        params = {
            'q': location
        }
        encoded_params = urllib.parse.urlencode(params)
        url = f"{NOMINATIM_API_BASE_URL}?{encoded_params}&format=json"
        response = requests.get(url)
        data = response.json()
        session['lat'] = data[0]['lat']
        session['lon'] = data[0]['lon']


    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True #DELETE THIS LATER AFTER U DONE TESTING
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("FINISHED LOGIN")
    return redirect(auth_url)


@app.route('/callback')
def callback():
    print("STARTED CALLBACK")

    if 'error' in request.args:
        return jsonify({'error': request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.datetime.now().timestamp() + token_info['expires_in']

        return redirect('/artists')


@app.route('/artists')
def get_artists():
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    #response_playlists = requests.get(API_BASE_URL + 'me/playlists', headers=headers)
    # playlists = response_playlists.json() #gives the actual data
    # playlists_names = []
    # for playlist in playlists['items']:
    #     playlists_names.append(playlist['name'])
    # return jsonify(playlists_names)

    artists_names = []

    #artists short term
    response_artists_short = requests.get(API_BASE_URL + 'me/top/artists?limit=50&time_range=short_term', headers=headers)
    artists_short = response_artists_short.json()

    for artist_short in artists_short['items']:
        artists_names.append(artist_short['name'])

    #artists medium term
    response_artists_medium = requests.get(API_BASE_URL + 'me/top/artists?limit=50', headers=headers)
    artists_medium = response_artists_medium.json()

    for artist_medium in artists_medium['items']:
        if artist_medium['name'] not in artists_names:
            artists_names.append(artist_medium['name'])


    #artists long term
    response_artists_long = requests.get(API_BASE_URL + 'me/top/artists?limit=50&time_range=long_term', headers=headers)
    artists_long = response_artists_long.json()

    for artist_long in artists_long['items']:
        if artist_long['name'] not in artists_names:
            artists_names.append(artist_long['name'])


    # tracks short term
    response_tracks_short = requests.get(API_BASE_URL + 'me/top/tracks?limit=50&time_range=short_term', headers=headers)
    tracks_short = response_tracks_short.json()

    for track_short in tracks_short['items']:
        artist = track_short['album']['artists'][0]['name']
        if artist not in artists_names:
            artists_names.append(artist)



    #tracks medium term
    response_tracks = requests.get(API_BASE_URL + 'me/top/tracks?limit=50', headers=headers)
    tracks = response_tracks.json()

    for track in tracks['items']:
        artist = track['album']['artists'][0]['name']
        if artist not in artists_names:
            artists_names.append(artist)


    # tracks long term
    response_tracks_long = requests.get(API_BASE_URL + 'me/top/tracks?limit=50&time_range=long_term', headers=headers)
    tracks_long = response_tracks_long.json()

    for track_long in tracks_long['items']:
        artist = track_long['album']['artists'][0]['name']
        if artist not in artists_names:
            artists_names.append(artist)

    #MOVING ONTO SEARCHING FOR EVENTS HOORAY

    events = {}
    lat_lon_string = f"{session['lat']},{session['lon']}"
    print(lat_lon_string)
    for artist in artists_names:
        params = {
            'apikey': TICKETMASTER_API_KEY,
            'size': 1,
            'keyword': artist,
            'latlong' : lat_lon_string,
            'radius': 70
        }
        url = TICKETMASTER_API_BASE_URL + 'events.json'
        concert_info = requests.get(url, params=params)
        print(artist + ": " + str(concert_info))
        if concert_info.status_code == 200:
            concert_info_json = concert_info.json()



            totalElements = concert_info_json['page']['totalElements']
            if totalElements > 0:
                print("--> " + artist + "has Elements")
                # making sure that the EXACT artist is in this
                # attractions = concert_info_json['_embedded']['events'][0]['_embedded']['attractions']
                # attraction_names = [attraction['name'] for attraction in attractions]
                # exact = False
                # if artist in attraction_names:
                #     exact = True

                event_name = concert_info_json["_embedded"]["events"][0]["name"]
                keywords = ['NIGHT', 'PARTY', 'TRIBUTE', 'REMIX']
                contains_keyword = any(keyword in event_name.upper() for keyword in keywords)

                noKeyWords = False
                exact = False
                if not contains_keyword:
                    noKeyWords = True

                attractions = concert_info_json['_embedded']['events'][0].get('_embedded', {}).get('attractions', [])
                if attractions:

                    attraction_names = [attraction['name'] for attraction in attractions]

                    if artist in attraction_names:
                        exact = True
                else:
                    exact = True

                if exact and noKeyWords:
                    start_date_str = concert_info_json['_embedded']['events'][0]['dates']['start']['localDate']
                    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%m/%d')
                    venue_name = concert_info_json['_embedded']['events'][0]['_embedded']['venues'][0]['name']
                    venue_address = concert_info_json['_embedded']['events'][0]['_embedded']['venues'][0]['address'][
                        'line1']
                    venue_city = concert_info_json['_embedded']['events'][0]['_embedded']['venues'][0]['city']['name']
                    link = concert_info_json['_embedded']['events'][0]['url']
                    print(link)
                    events[artist] = {
                        'start_date': start_date,
                        'venue_name': venue_name,
                        'venue_address': venue_address,
                        'venue_city': venue_city,
                        'link': link
                    }
    sorted_events = sorted(events.items(), key=lambda x: x[1]['start_date'])
    #print(sorted_events)

    # Convert start_date strings to datetime objects
    # for event_info in events.values():
    #     event_info['start_date'] = datetime.datetime.strptime(event_info['start_date'], '%Y-%m-%d')
    #
    # # Sort events by start_date
    # sorted_events = dict(sorted(events.items(), key=lambda x: x[1]['start_date']))

    # Now 'sorted_events' contains the events sorted by start date

    #return jsonify(sorted_events)
    print("RENDERING TEMPLATE")
    if len(sorted_events) > 0:
        return render_template("events2.html", events=sorted_events)
    else:
        return render_template("noDisplay.html")


@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET

        }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()

    session['access_token'] = new_token_info['access_token']
    session['expires_at'] = datetime.datetime.now().timestamp() + token_info['expires_in']

    return redirect('/artists')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)