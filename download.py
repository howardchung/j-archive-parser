from bs4 import BeautifulSoup
import re
import os
import sys
import time
import requests
import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_FOLDER = os.path.join(CURRENT_DIR, 'html')
# NUM_THREADS = 1
# NUM_THREADS = multiprocessing.cpu_count()

def main():
	create_save_folder()
	# Season 41 is 2024-2025, so e.g. in 2025 we want to do 41 and 42
	# today = datetime.date.today()
	# year = today.year
	# startSeason = year - 1984
	# Pick a season to start at. We can bump this occasionally once season is complete
	# but can't compute dynamically since we might miss episodes if we don't update for a while
	# To fix we need to resolve the last episode number back to a season number and start there
	startSeason = 41
	# python range is exclusive
	seasons = list(range(startSeason,startSeason + 2))
	# Add special seasons (if complete, only need to process once when added)
	# seasons.extend(['cwcpi', 'jm', 'pcj', 'ncc', 'goattournament', 'bbab', 'superjeopardy', 'trebekpilots'])
	for season in seasons:
		download_season(season)

def create_save_folder():
	if not os.path.isdir(SITE_FOLDER):
		sys_print("Creating {} folder".format(SITE_FOLDER))
		os.mkdir(SITE_FOLDER)

def download_season(season):
	sys_print('Downloading Season {}'.format(season))
	seasonPage = requests.get('https://j-archive.com/showseason.php?season={}'.format(season))
	seasonSoup = BeautifulSoup(seasonPage.text, 'html.parser')
	epIdRe = re.compile(r'game_id=(\d+)')
	epNumRe = re.compile(r'\#(\d{1,4})')
	episodeRe = re.compile(r'showgame\.php\?game_id=[0-9]+')
	episodeLinks = [link for link in seasonSoup.find_all('a') if episodeRe.match(link.get('href'))][::-1]
	for link in episodeLinks:
		prefix = "" if isinstance(season, int) else season + "_"
		episodeNumber = epNumRe.search(link.text.strip()).group(1)
		gameFile = os.path.join(SITE_FOLDER,'{}.html'.format(prefix + episodeNumber))
		if not os.path.isfile(gameFile):
			episodeId = epIdRe.search(link['href']).group(1)
			gamePage = requests.get('https://j-archive.com/showgame.php?game_id={}'.format(episodeId))
			open(gameFile, 'wb').write(gamePage.content)
			time.sleep(2)
	sys_print('Season {} finished'.format(season))

def sys_print(string):
	sys.stdout.write("{}\n".format(string))
	sys.stdout.flush()

if __name__=="__main__":
	main()
