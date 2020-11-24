from functools import partial
from os.path import basename, splitext
from urllib.parse import urldefrag, urlparse

from html5lib import parse
from httpx import ConnectTimeout
from trio import open_file

INDEX = 'https://dantri.com.vn/suc-khoe.htm'

parse_html5 = partial(parse, namespaceHTMLElements=False)


def articles(links):
    """Return URLs to vaccine articles from the given links."""
    for a in links:
        url, fragment = urldefrag(a.get('href'))
        if url.endswith('.html') and 'vaccine' in url: yield url


async def download(img, dest, client):
    """Save the given image with caption if it's about vaccine."""
    caption, url = img.get('alt'), img.get('data-src')
    if 'vaccine' not in caption.lower(): return
    name, ext = splitext(basename(urlparse(url).path))
    directory = dest / name
    await directory.mkdir(parents=True, exist_ok=True)

    try:
        fi = await client.get(url)
    except ConnectTimeout:
        return
    async with await open_file(directory/f'image{ext}', 'wb') as fo:
        async for chunk in fi.aiter_bytes(): await fo.write(chunk)
    await (directory/'caption').write_text(caption)
    print(caption)


async def scrape_images(url, dest, client, nursery):
    """Download vaccine images from the given Dantri article."""
    article = await client.get(url)
    for img in parse_html5(article.text).iterfind('.//img'):
        if img.get('itemprop') == 'contentUrl':
            nursery.start_soon(download, img, client, dest)


async def vnexpress(dest, client, nursery):
    """Download vaccine images from Dantri."""
    index = await client.get(INDEX)
    for url in set(articles(parse_html5(index.text).iterfind('.//a'))):
        nursery.start_soon(scrape_images, url, dest/'dantri',
                           client, nursery)

	  