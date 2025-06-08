# GZCTF-Cloner
.: Easily duplicate GZCTF games and challenges across instances :.

✅ Supports cloning of:
- Game metadata and settings
- Challenge titles, descriptions, and scores
- Flags and hints
- Local and remote attachments (with automatic re-upload)

> [!WARNING]
> Cloned games are hidden and require an invitation code per default. Please adjust game settings to your needs.
> All cloned challenges are disabled by default to prevent unintended exposure and to require manual review before publishing.

## Usage

>[!TIP]
>The script requires administrative cookie sessions to work.
>Please obtain your `GZCTF_Token` cookie(s) via developer tools.
>You can also find a dockerized version [here](https://github.com/l4rm4nd/GZCTF-Cloner/pkgs/container/gzctf-cloner).

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

The script will display all available challenges and prompt you for the challenges to clone as well as for a new game name.

### Cloning Across Different GZCTF Instances

If you'd like to clone games/challenges accross different GZCTF instances:

````
# clone single ctf game
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token 'GZCTF_Token-<COOKIE-1>' --dst-url 'https://ctf2.example.com' --dst-token 'GZCTF_Token-<COOKIE-2>'

# clone specific challenges accross games
python3 gzctf_cloner.py --url 'https://ctf.example.com' --token 'GZCTF_Token-<COOKIE-1>' --dst-url 'https://ctf2.example.com' --dst-token 'GZCTF_Token-<COOKIE-2>' --newgame
````
