# -*- coding: utf-8 -*-

import os
import flask
import json
import requests

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.oauth2 import id_token
from pymongo import MongoClient
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "secret.json"

# The OAuth 2.0 access scope allows for access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/calendar.readonly',
          "openid",
          "https://www.googleapis.com/auth/userinfo.email",
          "https://www.googleapis.com/auth/userinfo.profile"]
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

app = flask.Flask(__name__)
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = "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"

mongodb_client = MongoClient("mongodb+srv://mjs37_db_user:ditcCwkVknOhnePC@recruiting.nb4whlh.mongodb.net/")

users_db = mongodb_client["users"]

users_collection = users_db["users"]

@app.route('/')
def index():
  return print_index_table()

@app.route('/drive')
def drive_api_request():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')

  features = flask.session['features']

  if features['drive']:
    # Load client secrets from the server-side file.
    with open(CLIENT_SECRETS_FILE, 'r') as f:
        client_config = json.load(f)['web']

    # Load user-specific credentials from browser session storage.
    session_credentials = flask.session['credentials']

    # Reconstruct the credentials object.
    credentials = google.oauth2.credentials.Credentials(
        refresh_token=session_credentials.get('refresh_token'),
        scopes=session_credentials.get('granted_scopes'),
        token=session_credentials.get('token'),
        client_id=client_config.get('client_id'),
        client_secret=client_config.get('client_secret'),
        token_uri=client_config.get('token_uri'))

    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    files = drive.files().list().execute()

    # Save credentials back to session in case access token was refreshed.
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.jsonify(**files)
  else:
    # User didn't authorize read-only Drive activity permission.
    return '<p>Drive feature is not enabled.</p>'

@app.route('/calendar')
def calendar_api_request():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')

  features = flask.session['features']

  if features['calendar']:
    # User authorized Calendar read permission.
    # Calling the APIs, etc.
    return ('<p>User granted the Google Calendar read permission. '+
            'This sample code does not include code to call Calendar</p>')
  else:
    # User didn't authorize Calendar read permission.
    # Update UX and application accordingly
    return '<p>Calendar feature is not enabled.</p>'

@app.route('/authorize')
def authorize():
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

  # The URI created here must exactly match one of the authorized redirect URIs
  # for the OAuth 2.0 client, which you configured in the API Console. If this
  # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
  # error.
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
  flask.session['state'] = state
  flask.session['code_verifier'] = flow.code_verifier

  return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    state=state,
    code_verifier=flask.session.pop('code_verifier')
)
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  credentials = flow.credentials

  # Save credentials in session

  flask.session["credentials"] = credentials_to_dict(credentials)

  # Check granted scopes

  features = check_granted_scopes(flask.session["credentials"])

  flask.session["features"] = features

  # Get Google ID token

  google_id_token = credentials.id_token

  if not google_id_token:

      return "Google ID token missing. Ensure 'openid' is in your scopes.", 400

  # Verify Google ID token

  try:

    user_info = id_token.verify_oauth2_token(

        google_id_token,

        GoogleRequest(),

        "240724484773-u2caekia4337vnrof7v337et4acbvdi8.apps.googleusercontent.com"

)

  except ValueError as e:

      return f"Invalid Google ID token: {str(e)}", 401

  # Extract user information

  google_id = user_info.get("sub")

  email = user_info.get("email")

  name = user_info.get("name")

  picture = user_info.get("picture")

  # Verify required information

  if not google_id or not email:

      return "Missing required Google account information.", 400

  # Look up user by permanent Google ID

  user = users_collection.find_one({"google_id": google_id})

  if not user:

      user_document = {

          "email": email,

          "name": name,

          "google_id": google_id,

          "picture": picture,

          "role": "applicant"

      }

      users_collection.insert_one(user_document)

      flask.session["google_id"] = google_id

      return flask.redirect("/")

  else:

      flask.session["google_id"] = google_id

      return flask.redirect("/clear")




  
  
@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  # Load client secrets from the server-side file.
  with open(CLIENT_SECRETS_FILE, 'r') as f:
      client_config = json.load(f)['web']

  # Load user-specific credentials from the session.
  session_credentials = flask.session['credentials']

  # Reconstruct the credentials object.
  credentials = google.oauth2.credentials.Credentials(
      refresh_token=session_credentials.get('refresh_token'),
      scopes=session_credentials.get('granted_scopes'),
      token=session_credentials.get('token'),
      client_id=client_config.get('client_id'),
      client_secret=client_config.get('client_secret'),
      token_uri=client_config.get('token_uri'))

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    # Clear the user's session credentials after successful revocation
    if 'credentials' in flask.session:
        del flask.session['credentials']
        del flask.session['features']
    return('Credentials successfully revoked.' + print_index_table())
  else:
    return('An error occurred.' + print_index_table())

@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared.<br><br>' +
          print_index_table())

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'granted_scopes': credentials.granted_scopes}

def check_granted_scopes(credentials):
  features = {}
  if 'https://www.googleapis.com/auth/drive.metadata.readonly' in credentials['granted_scopes']:
    features['drive'] = True
  else:
    features['drive'] = False

  if 'https://www.googleapis.com/auth/calendar.readonly' in credentials['granted_scopes']:
    features['calendar'] = True
  else:
    features['calendar'] = False

  return features

def print_index_table():
  return ('<table>' + 
          '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
          '<td>Go directly to the authorization flow. If there are stored ' +
          '    credentials, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' +
          '<tr><td><a href="/drive">Call Drive API directly</a></td>' +
          '<td> Use stored credentials to call the API, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' +
          '<tr><td><a href="/calendar">Call Calendar API directly</a></td>' +
          '<td> Use stored credentials to call the API, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' + 
          '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
          '<td>Revoke the access token associated with the current user ' +
          '    session. After revoking credentials, if you go to the test ' +
          '    page, you should see an <code>invalid_grant</code> error.' +
          '</td></tr>' +
          '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
          '<td>Clear the access token currently stored in the user session. ' +
          '    After clearing the token, if you <a href="/authorize">authorize</a> ' +
          '    again, you should go back to the auth flow.' +
          '</td></tr></table>')

if __name__ == '__main__':
  # When running locally, disable OAuthlib's HTTPs verification.
  # ACTION ITEM for developers:
  #     When running in production *do not* leave this option enabled.
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

  # This disables the requested scopes and granted scopes check.
  # If users only grant partial request, the warning would not be thrown.
  os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

  # Specify a hostname and port that are set as a valid redirect URI
  # for your API project in the Google API Console.
  app.run('localhost', 8080, debug=True)