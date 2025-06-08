# GZCTF-Cloner
Python 3 Script to Clone [GZCTF](https://github.com/GZTimeWalker/GZCTF) Games and Challenges

## Usage

>[!TIP]
>The script requires administrative cookie sessions to work.
>Please obtain your `GZCTF_Token` cookie(s) via developer tools.
>
>You can also find a dockerized version as [GHCR.IO package](https://github.com/l4rm4nd/GZCTF-Cloner/pkgs/container/gzctf-cloner).

````
usage: gzctf_cloner.py [-h] --url URL --token TOKEN [--invite-code INVITE_CODE] [--newgame] [--dst-url DST_URL]
                       [--dst-token DST_TOKEN]

GZCTF Cloner via Token

options:
  -h, --help                    show this help message and exit
  --url URL                     Source base URL
  --token TOKEN                 GZCTF_Token for source session
  --invite-code INVITE_CODE     Custom invite code
                              
  --newgame                     New game from selected challenges
  --dst-url DST_URL             Destination base URL
  --dst-token DST_TOKEN         Destination GZCTF_Token
````

### Cloning Single Game

If you'd like to clone a single CTF game to the same instance:

````
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token '<GZCTF_Token>'
````

The script will display games and prompt you for the game and challenges to clone.

### Cloning Specific Challenges Across All Games

If you'd like to clone specific CTF challenges across all games:

````
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token '<GZCTF_Token>' --newgame
````

The script will display all available challenges and prompt you for the challenges to clone.

### Cloning Across Different GZCTF Instances

If you'd like to clone games/challenges accross different GZCTF instances:

````
# clone single ctf game
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token 'GZCTF_Token-<COOKIE-1>' --dst-url 'https://ctf2.example.com' --dst-token 'GZCTF_Token-<COOKIE-2>'

# clone specific challenges accross games
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token 'GZCTF_Token-<COOKIE-1>' --dst-url 'https://ctf2.example.com' --dst-token 'GZCTF_Token-<COOKIE-2>' --newgame
````

# Caviats

>[!WARNING]
> This Python script will duplicate games and challenges with nearly all meta data (descriptions, hints, flags, scores).
>
> Attachments are not re-uploaded though. The script will use the existing (local) asset url and just define a new remote url using the instance's url. If you are cloning accross instances, I recommend re-uploading attachments.
