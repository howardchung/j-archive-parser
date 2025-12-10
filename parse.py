from __future__ import print_function
from bs4 import BeautifulSoup
import time
import sys
import os
import re
import csv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_FOLDER = os.path.join(CURRENT_DIR, "html")
SAVE_FOLDER = os.path.join(CURRENT_DIR, "csv")
# NUM_THREADS = 1
# NUM_THREADS = multiprocessing.cpu_count()

def main():
	create_save_folder()
	parse_season()

#Create a folder, if there isn't already one, to save csv in
def create_save_folder():
    if not os.path.isdir(SAVE_FOLDER):
        print("Creating {} folder".format(SAVE_FOLDER))
        os.mkdir(SAVE_FOLDER)
	
def parse_season():
	folder = os.path.join(SITE_FOLDER)
	files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

	for file_i in range(len(files)):
		saveFile = os.path.join(SAVE_FOLDER, files[file_i].split('/')[-1] + '.csv')
    	# skip if output filename already exists
		if os.path.isfile(saveFile):
			# print('Skipping {}'.format(files[file_i]))
			continue
		# Create csv file in write mode with utf-8 encoding
		with open(saveFile,'w',newline='',encoding='utf-8') as csvfile:
			# Set up csv writer
			episodeWriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
			# Write titles to csv file
			episodeWriter.writerow(['epNum', 'airDate', 'extra_info', 'round_name', 'coord', 'category', 'order', 'value', 'daily_double', 'question', 'answer', 'correctAttempts', 'wrongAttempts'])
			print('Parsing episode {}/{} {}'.format(file_i + 1, len(files), files[file_i]), flush=True)
			try:
				ep = parse_episode(files[file_i])
				if ep:
					ep = [[[clueElement for clueElement in clue] for clue in round] for round in ep]
					for round in ep:
						for question in round:
							episodeWriter.writerow(question)
			except Exception as e:
				raise e

def parse_episode(fileName):
	#Get episode page
	episode = open(fileName, encoding="utf-8")
	soupEpisode = BeautifulSoup(episode, 'html.parser')
	episode.close()

	#Get episode number (different from ID) from page title
	# epNum = re.search(r'#(\d+)', soupEpisode.title.text).group(1)
	# Switch to getting the epNum from the filename to handle special seasons
	epNum = fileName.split('/')[-1].split('.')[0]
	#Get extra info about episode from top of page
	extraInfo = soupEpisode.find('div', id='game_comments').text
	#Check for special season names (Super Jeopardy, Trebek Pilots, anything non-number)
	# sj = re.compile(r'(Super Jeopardy!) show #(\d+)')
	# if sj.search(soupEpisode.title.text):
	# 	epNum = ' '.join(sj.search(soupEpisode.title.text).groups())
	# trbk = re.compile(r'(Trebek pilot) #(\d+)')
	# if trbk.search(soupEpisode.title.text):
	# 	epNum = ' '.join(trbk.search(soupEpisode.title.text).groups())
	#Get episode air date from page title (format YYYY-MM-DD)
	airDate = re.search(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', soupEpisode.title.text).group()

	#Booleans to check if page has each round type
	hasRoundJ = True if soupEpisode.find(id='jeopardy_round') else False
	hasRoundDJ = True if soupEpisode.find(id='double_jeopardy_round') else False
	hasRoundTJ = True if soupEpisode.find(id='triple_jeopardy_round') else False
	hasRoundFJ = True if soupEpisode.find(id='final_jeopardy_round') else False
	hasRoundTB = True if len(soupEpisode.find_all(class_='final_round')) > 1 else False

	parsedRounds = []

	#For each round type, if exists in page, parse
	if hasRoundJ:
		j_table = soupEpisode.find(id='jeopardy_round')
		#Pass epNum and airDate to so all info can be added into array as a question at once
		parsedRounds.append(parse_round(0, j_table, epNum, airDate, extraInfo))

	if hasRoundDJ:
		dj_table = soupEpisode.find(id='double_jeopardy_round')
		#Pass epNum and airDate to so all info can be added into array as a question at once
		parsedRounds.append(parse_round(1, dj_table, epNum, airDate, extraInfo))

	if hasRoundTJ:
		tj_table = soupEpisode.find(id='triple_jeopardy_round')
		#Pass epNum and airDate to so all info can be added into array as a question at once
		parsedRounds.append(parse_round(2, tj_table, epNum, airDate, extraInfo))

	if hasRoundFJ:
		fj_table = soupEpisode.find(id='final_jeopardy_round').find_all(class_='final_round')[0]
		#Pass epNum and airDate to so all info can be added into array as a question at once
		parsedRounds.append(parse_round(3, fj_table, epNum, airDate, extraInfo))
	
	if hasRoundTB:
		tb_table = soupEpisode.find(id='final_jeopardy_round').find_all(class_='final_round')[1]
		parsedRounds.append(parse_round(4, tb_table, epNum, airDate, extraInfo))

	#Some episodes have pages, but don't have any actual episode content in them
	if parsedRounds:
		return parsedRounds
	else:
		return None

#Parse a single round layout (Jeoparyd, Double Jeopardy, Final Jeopardy)
#Final is different than regular and double. Only has a single clue, and has multiple responses and bets.
def parse_round(round, table, epNum, airDate, extraInfo):
	roundClues = []
	if round < 3:
		#Get list of category names
		categories = [cat.text for cat in table.find_all('td', class_='category_name')]
		#Variable for tracking which column (category) currently getting clues from
		x = 0
		for clue in table.find_all('td', class_='clue'):
			exists = True if clue.text.strip() else False
			if exists:
				#Clue text <td> has id attribute in the format clue_round_x_y, one indexed
				#Extract coordinates from id text
				coord = tuple([int(x) for x in re.search(r'(\d)_(\d)', clue.find('td', class_='clue_text').get('id')).groups()])
				valueRaw = clue.find('td', class_=re.compile('clue_value')).text
				#Strip down value text to just have number (daily doubles have DD:)
				try:
					value = (int(valueRaw.lstrip('D: $').replace(',','')),)
				except:
					value = (-100,)
				question = clue.find('td', class_='clue_text').text
				#Answers to questions (both right and wrong) are in hover, each with a class to specify color
				old_answer = BeautifulSoup(clue.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find('em', class_='correct_response')
				# new answer format is just in the html rather than buried in onmouseover
				new_answer = clue.find('em', class_='correct_response')
				if new_answer:
					answer = new_answer.text
				elif old_answer:
					answer = old_answer.text
				else:
					raise Exception("error in answer parsing")
				daily_double = True if re.match(r'DD:', valueRaw) else False	
				wrong = BeautifulSoup(clue.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='wrong')
				n = len(wrong)
				for w in wrong:
					#Sometimes instead of showing all three incorrect responses will just show 'Triple Stumper'
					#(also sometimes has 'Triple Stumper' as well as other wrong responses)
					if re.match(r'Triple Stumper', w.text):
						n = 3
				wrongAttempts = n
				#Some odd situations with more than one correct response
				correctAttempts = len(BeautifulSoup(clue.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='right'))
				#Doesn't actually get used
				totalAttemps = wrongAttempts + correctAttempts
				order = clue.find('td', class_='clue_order_number').text
				category = categories[x]
				if round == 1:
					round_name = 'Double Jeopardy'
				elif round == 2:
					round_name = 'Triple Jeopardy'
				else:
					round_name = 'Jeopardy'
				#Add all retrieved data onto array
				# print(epNum, airDate, round_name, coord, valueRaw, value, question, answer, daily_double)
				roundClues.append([epNum, airDate, extraInfo, round_name, coord, category, order, value, daily_double, question, answer, correctAttempts, wrongAttempts])
			#Tracking current column
			x = 0 if x == 5 else x + 1
	elif round == 3:
		#Final Jeopardy
		coord = (1,1)
		rawValue = [x.text for x in BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all(lambda tag: tag.name == 'td' and not tag.attrs)]
		value = tuple([int(v.lstrip('D: $').replace(',','')) for v in rawValue])
		question = table.find('td', id='clue_FJ').text

		#Answers to questions (both right and wrong) are in hover, each with a class to specify color
		old_answer = BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find('em')
		# new answer format is just in the html rather than buried in onmouseover
		new_answer = table.find('em', class_='correct_response')
		if new_answer:
			answer = new_answer.text
		elif old_answer:
			answer = old_answer.text
		else:
			raise Exception("error in answer parsing")

		daily_double = False
		wrongAttempts = len(BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='wrong'))
		correctAttempts = len(BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='right'))
		totalAttemps = wrongAttempts + correctAttempts
		order = 0
		category = table.find('td', class_='category_name').text
		round_name = 'Final Jeopardy'
		roundClues.append([epNum, airDate, extraInfo, round_name, coord, category, order, value, daily_double, question, answer, correctAttempts, wrongAttempts])
	else:
		#Tiebreaker round
		coord = (1,1)
		value = ()
		question = table.find('td', id='clue_TB').text
		answer = BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find('em')
		daily_double = False
		wrongAttempts = len(BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='wrong'))
		correctAttempts = len(BeautifulSoup(table.find('div', onmouseover=True).get('onmouseover'), 'html.parser').find_all('td', class_='right'))
		totalAttemps = wrongAttempts + correctAttempts
		order = 0
		category = table.find('td', class_='category_name').text
		round_name = 'Tiebreaker'
		roundClues.append([epNum, airDate, extraInfo, round_name, coord, category, order, value, daily_double, question, answer, correctAttempts, wrongAttempts])
	return roundClues

if __name__ == "__main__":
	main()
