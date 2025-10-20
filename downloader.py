import os
import re
import urllib.parse as urlparse
import urllib.request as urllib2
from bs4 import BeautifulSoup

BASE_URL = 'https://downloads.khinsider.com'


def safe_url(url):
    return urlparse.quote(url, safe=':/?&=%')


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*\r\n]+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > 80:
        name = name[:80].rstrip()
    return name


def validate_url(url):
    return '//downloads.khinsider.com/game-soundtracks/album/' in url


def clean_song_title(raw_title):
    """
    Removes album/game info and leftover words like 'MP3', 'OST', 'Download', etc.
    Example input:
      'Stephanie\'s Visit (Extended) MP3 - Kingdom Come Deliverance – OST Atmospheres &'
    Output:
      'Stephanie\'s Visit (Extended)'
    """
    # Split before " MP3" or " OST" or " Download"
    raw_title = re.split(r'\b(?:MP3|OST|Download)\b', raw_title, 1)[0]
    # Remove trailing dashes or junk
    raw_title = re.sub(r'[-–]+$', '', raw_title).strip()
    return raw_title


def fetch_from_url(url):
    url = url.strip()
    if not url:
        print('[error] Invalid url: (empty line)')
        return
    if not validate_url(url):
        print('[error] Invalid url: ' + url)
        return

    print('[info] Url found: ' + url)

    base_dir = 'downloads'
    album_name = url.split('/')[-1]
    dir_name = os.path.join(base_dir, album_name)

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    print('[info] crawling for links...')
    response = urllib2.urlopen(safe_url(url))
    soup = BeautifulSoup(response, features="lxml")

    song_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.mp3') and '/game-soundtracks/album/' in href:
            full = BASE_URL + href
            if full not in song_links:
                song_links.append(full)

    if not song_links:
        print('[error] Could not find any songs on page.')
        return

    print(f'[info] {len(song_links)} links acquired')

    downloaded_mp3s = {}
    track_num = 1

    for song_url in song_links:
        try:
            song_page = urllib2.urlopen(safe_url(song_url))
            link_soup = BeautifulSoup(song_page, features="lxml")
            audio = link_soup.find('audio')
            if not audio:
                print(f'[warn] No audio found for: {song_url}')
                continue

            mp3_url = audio.get('src')
            if not mp3_url:
                print(f'[warn] Missing mp3 src for: {song_url}')
                continue

            if mp3_url in downloaded_mp3s:
                continue
            downloaded_mp3s[mp3_url] = True

            title_tag = link_soup.find('title')
            raw_title = title_tag.text if title_tag else os.path.basename(mp3_url)

            song_name = clean_song_title(raw_title)
            song_name = sanitize_filename(song_name)
            if not song_name:
                song_name = f"track_{track_num:03d}"

            file_name = f"{track_num:03d} - {song_name}.mp3"
            track_num += 1

            file_on_disk_path = os.path.join(dir_name, file_name)

            mp3file = urllib2.urlopen(safe_url(mp3_url))
            meta = mp3file.info()
            file_size = float(meta.get("Content-Length", 0)) / 1_000_000

            if os.path.exists(file_on_disk_path):
                stat = os.stat(file_on_disk_path)
                same_size = round(stat.st_size / 1_000_000, 2) == round(file_size, 2)
                if same_size:
                    print(f'[skipping] "{file_name}" already downloaded.')
                    continue

            print(f'[downloading] {file_name} [{file_size:.2f}MB]')
            with open(file_on_disk_path, 'wb') as output:
                output.write(mp3file.read())
            print(f'[done] "{file_name}"')

        except Exception as e:
            print(f'[error] Failed to download from {song_url}: {e}')


input_file_name = 'inputs.txt'
if os.path.exists(input_file_name):
    print('[info] Input file found. Parsing for links...')
    with open(input_file_name, 'r') as file:
        for line in file:
            fetch_from_url(line)
else:
    print('Please input link in quotes to album on khinsider.')
    print('Example input:')
    print('  http://downloads.khinsider.com/game-soundtracks/album/disgaea-4-a-promise-unforgotten-soundtrack')
    url = input('Url: ')
    fetch_from_url(url)
