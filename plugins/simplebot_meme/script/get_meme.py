import bs4
import requests

URL = 'https://m.cuantarazon.com/aleatorio'

HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}

with requests.get(URL, headers=HEADERS) as r:
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, 'html.parser')

img_url = soup.find('div', class_='storyContent').find('img')['src'].split('?')[0]
print(img_url)

with requests.get(img_url, headers=HEADERS) as r:
    r.raise_for_status()

    with open('meme.jpg', 'wb') as fd:
        fd.write(r.content)
