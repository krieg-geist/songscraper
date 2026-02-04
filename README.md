# songscraper

Tiny CLI to grab Guitar Pro files from Songsterr. Can grab from url or do an interactive search.

## Quick start

- Install deps: `pip install requests`
- Run:
  - Single URL: `python songscraper.py https://www.songsterr.com/a/wsa/amebix-chain-reaction-tab-s68807`
  - Multiple URLs: `python songscraper.py URL1 URL2 URL3`
  - Search terms + pick interactively: `python songscraper.py -i viagra boys sports`
  - Choose a revision interactively: `python songscraper.py -i https://www.songsterr.com/a/wsa/amebix-chain-reaction-tab-s68807`
  - From a file of URLs: `python songscraper.py -f urls.txt`
  - From stdin: `cat urls.txt | python songscraper.py -f -`
  - Custom output dir: `python songscraper.py -o ./tabs URL1`
  - More search results: `python songscraper.py -i --max-results 50 meshuggah`

Downloads land in `./output` by default.

### Note
- Feel free to adapt this to suit your own needs
- Should work until the next time they mess with the API
- Use responsibly — I’m not responsible for any ToS violations.
