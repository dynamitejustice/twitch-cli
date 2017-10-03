#!/usr/bin/python3
import os
import sys
import requests
import subprocess
import json
import argparse
from urllib.parse import urlencode
import webbrowser

def get_config_dir():
    if os.name == 'nt':
        return os.path.join(os.environ['APPDATA'], 'twitch-cli')
    elif os.name == 'posix':
        home = os.environ.get('XDG_CONFIG_HOME', '~/.config')
        return os.path.expanduser(os.path.join(home, 'twitch-cli'))

# The configuration file is located at $HOME/.config/twitch-cli/config.json.
CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

TWITCH_CLIENT_ID = 'e0fm2z7ufk73k2jnkm21y0gp1h9q2o'

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, sort_keys=True, indent=4)

def load_config():
    """Load the configuration file at ~/.config/twitch-cli/config.json and
    return a dict with configuration options."""

    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'a') as f:
            f.write('{}')
        print('Configuration file created at {}'.format(CONFIG_FILE))

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    config.setdefault('oauth', '')

    save_config(config)

    return config

config = load_config()

def main():
    parser = argparse.ArgumentParser(description='List or play Twitch streams.')
    subparsers = parser.add_subparsers(metavar='COMMAND')

    parser_list = subparsers.add_parser('list', help='List followed channels')
    parser_list.add_argument('--flat', '-f', action='store_true', help='Don\'t show detailed information or prompt')
    parser_list.set_defaults(func=cmd_list)

    parser_play = subparsers.add_parser('play', help='Play a stream')
    parser_play.add_argument('channel', help='Channel name')
    parser_play.set_defaults(func=cmd_play)

    parser_auth = subparsers.add_parser('auth', help='Authenticate with Twitch')
    parser_auth.set_defaults(func=cmd_auth)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        args = parser.parse_args(['list'])

    args.func(args)

# The cmd_* functions get called when their respective subcommand is executed
# Example: "python3 twitch-cli list" calls "cmd_list"

def cmd_list(args):
    list_streams(args)

def cmd_play(args):
    play_stream(args.channel)

def cmd_auth(args):
    if config['oauth'] != '':
        print('You are already authenticated.')
        return

    token = authenticate()

    if token != '':
        config['oauth'] = token
        save_config(config)
        print('Authentication complete.')
    else:
        print('Authentication cancelled.')

def play_stream(channel):
    """Load a stream and open the player"""

    command = 'streamlink twitch.tv/{} best '.format(channel)

    process = subprocess.Popen(command.split(), stdout=None, stderr=None)
    output, error = process.communicate()

def list_streams(args):
    """Load the list of streams and prompt the user to chose one."""

    if config['oauth'] == '':
        print('You have to provide a Twitch OAuth token to list followed '
              'streams.')
        print('Look at the configuration file at {}'.format(CONFIG_FILE))
        sys.exit(1)

    url = 'https://api.twitch.tv/kraken/streams/followed'
    headers = {
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Authorization': 'OAuth {}'.format(config['oauth'])
    }
    request = requests.get(url, headers=headers)
    response = request.json()

    if 'streams' not in response:
        print('Something went wrong while trying to fetch data from the '
              'Twitch API')
        sys.exit(1)

    print_stream_list(response['streams'], title='Streams online now',
                      flat=args.flat)

    if not args.flat:
        selection = input('Stream ID: ')
        try:
            selection = int(selection)
        except:
            return
    else:
        return

    if selection > len(response['streams']):
        return

    play_stream(response['streams'][selection - 1]['channel']['name'], config)

def get_followed_streams():
    pass

def print_stream_list(streams, title=None, flat=False):
    if title and not flat:
        print(title)
        print('')

    if flat:
        format = '{1[channel][name]}'
    else:
        ind_len = len(str(len(streams)))
        format = ('{0: >' + str(ind_len + 2) + 's} {1[channel][display_name]}: '
                  '{1[channel][status]}\n' +
                  (' ' * (ind_len + 3)) + '{1[channel][name]} playing '
                  '{1[channel][game]} for {1[viewers]} viewers\n')

    i = 1
    for stream in streams:
        print(format.format('[' + str(i) + ']', stream))
        i += 1

def authenticate():
    query = {
        'client_id': TWITCH_CLIENT_ID,
        'redirect_uri': 'https://butt4cak3.github.io/twitch-cli/oauth.html',
        'response_type': 'token',
        'scope': ''
    }
    url = 'https://api.twitch.tv/kraken/oauth2/authorize/?{}'.format(urlencode(query))

    try:
        if not webbrowser.open_new_tab(url):
            raise webbrowser.Error
    except webbrowser.Error:
        print('Couldn\'t open a browser. Open this URL in your browser to continue:')
        print(url)
        return

    token = input('OAuth token: ')
    return token.strip()

if __name__ == '__main__':
    main()
