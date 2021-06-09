import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from time import sleep
import pathlib
import csv
import os
import face_recognition
import requests
import glob
import shutil
import urllib
from PIL import Image
import json
from typing import List


# -----------------------------------------------------------------------------
#
#	Domain objects
#		- manages the data domain
#		- ensures we are passing back the right types
#
# -----------------------------------------------------------------------------


# holds a login name and password for facebook
class Login(object):

	def __init__(self, login_email:str, password:str):
		self.login_email = login_email
		self.password = password


# holds the browser driver and login email for a successful login
class LoggedInSession(object):

	def __init__(self, driver:webdriver, login_email):
		self.driver = driver
		self.login_email = login_email


# holds the login emali for a failed login
class FailedLogin(object):

	def __init__(self, login_email:str):
		self.login_email = login_email


# holds the url of a target photo
class TargetPhoto(object):

	def __init__(self, url:str):
		self.url = url


# holds the full name of a target
class Target(object):

	def __init__(self, name):
		self.name = name


# holds the profile link and id of a name match
class NameMatch(object):

	def __init__(self, target_name:str, profile_link:str, id:int):
		self.target_name = target_name
		self.profile_link = profile_link
		self.id = id


# holds data on a matched face
class FaceMatch(object):

	def __init__(self, target_name:str, target_photo_url:str, match_profile_url:str, dist:float):
		self.target_name = target_name
		self.target_photo_url = target_photo_url
		self.match_profile = match_profile_url
		self.dist = dist


# holds the directory map and creates any that are missing
class Directories(object):

	def __init__(self, root_dir:str):
		self.unscanned_dir = f"{root_dir}/unscanned"
		self.working_dir = f"{root_dir}/working"
		self.suspect_dir = f"{root_dir}/suspect"
		self.completed_dir = f"{root_dir}/completed"
		self.temp_dir = f"{root_dir}/temp"

		if os.path.exists(self.unscanned_dir) == False:
			os.mkdir(self.unscanned_dir)

		if os.path.exists(self.working_dir) == False:
			os.mkdir(self.working_dir)

		if os.path.exists(self.suspect_dir) == False:
			os.mkdir(self.suspect_dir)

		if os.path.exists(self.completed_dir) == False:
			os.mkdir(self.completed_dir)

		if os.path.exists(self.temp_dir) == False:
			os.mkdir(self.temp_dir)


# -----------------------------------------------------------------------------
#
#	Facebook login functions
#		- get logins
#		- login to facebook and test connection
#
# -----------------------------------------------------------------------------


# given a login and password for facebook
# try to log in and return a browser session
def __try_login_to_facebook(login:Login, login_url:str):

	driver = webdriver.Chrome()
	
	driver.get(login_url)
	element = driver.find_element_by_id("email")
	element.send_keys(login.login_email)
	element = driver.find_element_by_id("pass")
	element.send_keys(login.password)
	element.send_keys(Keys.RETURN)

	return driver


# given a login and password for instagram
# try to log in and return a browser session
def __try_login_to_instagram(login:Login, login_url:str):

	driver = webdriver.Chrome()
	driver.get(login_url)

	sleep(3)

	element = driver.find_element_by_xpath("//input[@name='username']")
	element.send_keys(login.login_email)
	element = driver.find_element_by_xpath("//input[@name='password']")
	element.send_keys(login.password)
	driver.find_element_by_xpath("//button[@type='submit']").click()

	sleep(5)

	try:
		print("try to switch off notifcations")
		#driver.find_element_by_class_name("aOOlW").click()
		driver.find_element_by_xpath('//button[text()="Not Now"]').click()
		sleep(3)
		print("notifcations switched off")
	except ex:
		print(ex)
		pass

	return driver


# check if login button is still visible,
# and if so return fail
#def __login_successful(browser):
def __login_successful(driver:webdriver):

	sleep(3)

	try:
		# if the login button is visible, then the login must have failed...
		driver.find_element_by_id("loginbutton")
		return False
	except:
		return True


# given a login name/password and a login url
# try to log into facebook and return either a successful
# or unsuccessful session
def try_log_into_fb_broswer_session(login:Login, login_url:str):

	driver = __try_login_to_facebook(login, login_url)

	if __login_successful(driver):
		return LoggedInSession(driver, login.login_email)
	else:
		return FailedLogin(login.login_email)


# given a login name/password and a login url
# try to log into instagram and return either a successful
# or unsuccessful session
def try_log_into_ig_broswer_session(login:Login, login_url:str):

	driver = __try_login_to_instagram(login, login_url)

	try:
		return LoggedInSession(driver, login.login_email)
	except:
		return FailedLogin(login.login_email)


# load logins from file (login, password format)
# return list of Logins
def get_logins_from_file(url:str):

	with open(url, 'r') as file:

		csv_reader = csv.reader(file, delimiter=",")
		data = list(csv_reader)

		def make_login(line:str):
			login_email = line[0]
			password = line[1]
			login = Login(login_email, password)
			return login

		logins = list(map(lambda line: make_login(line), data))

		return logins



# -----------------------------------------------------------------------------
#
#	Target photo functions
#		- stage target photos
#		- unstage target photos in the case of failure
#		- move completed photos
#		- convert photo names to target names
#
# -----------------------------------------------------------------------------


# for a given login, take 100 photos from the unscanned pile
# move them to the working folder and return links to each
def stage_target_photos(dirs:Directories, num_photos=100):

	unscanned_photos = []

	unscanned_photos.extend(glob.glob(f"{dirs.unscanned_dir}/*.png"))

	unscanned_photos.extend(glob.glob(f"{dirs.unscanned_dir}/*.jpg"))

	if len(unscanned_photos) < num_photos:
		num_photos = len(unscanned_photos)

	working_photos = []

	for photo in unscanned_photos[0:num_photos]:
		filename = os.path.basename(photo)
		dest = f"{dirs.working_dir}/{filename}"
		shutil.move(photo, dest)
		target_photo = TargetPhoto(dest)
		working_photos.append(target_photo)

	return working_photos


# for a list of target photos
# move those that are still in working folder back into unscanned pile
# (used if an account starts to fail)
def unstage_target_photos(dirs:Directories, working_photos:List[TargetPhoto]):

	for photo in working_photos:
		if os.path.exists(photo.url):
			filename = os.path.basename(photo.url)
			dest = f"{dirs.unscanned_dir}/{filename}"
			shutil.move(photo.url, dest)


# for a list of target photos
# move those that are still in working folder back into unscanned pile
# (used if an account starts to fail)
def move_completed_photo(completed_photo:TargetPhoto, dirs:Directories, is_suspect:bool):

	filename = os.path.basename(completed_photo.url)

	# if the number of name matches was zero, then we may have a problem
	# in which case, move that target photo to Suspect for later analysi
	if is_suspect:
		dest = f"{dirs.suspect_dir}/{filename}"
		shutil.move(completed_photo.url, dest)
	# otherwise, move the photo to Completed
	else:
		dest = f"{dirs.completed_dir}/{filename}"
		shutil.move(completed_photo.url, dest)


# from a target photo, extracts the names and
# creates a list of Targets
def convert_target_photo_to_targets(target_photo:TargetPhoto):

	# get all the names referenced in the photo url 
	# (assuming we split multiple paedos by " & " in the photo name)
	names = os.path.basename(target_photo.url).split(" & ")

	targets = []

	for name in names:
		try:
			extension = pathlib.Path(name).suffix

			clean_name = name.replace(extension,"")
			targets.append(Target(clean_name))
		except:
			continue

	return targets


# -----------------------------------------------------------------------------
#
#	Facebook scraping and photo matching functions
#
# -----------------------------------------------------------------------------


# given a target, return the first page of search results
# from facebook. The optional_args are a string of space delimted extra terms
# to be appended to the search URL (i.e. "united kingdom")
# Returns a list of Potential Matches
def find_fb_name_matches(target:Target, optional_args:str, session:LoggedInSession):
	
	search_name = target.name.replace(" ", "%20")

	url = f"https://www.facebook.com/search/people/?q={search_name}"

	# add optional args if non-blank
	if optional_args != "":
		url = url + f"%20{optional_args}"

	session.driver.get(url)

	sleep(3)

	searchresponse = session.driver.page_source.encode('utf-8')
	soup = BeautifulSoup(searchresponse, 'html.parser')

	name_matches = []

	# search results are in a div with class=_401d
	for element in soup.find_all('div', {'class': '_401d'}):
		try:
			datagt = element['data-gt']
			stripped = datagt.replace("\\","")
			stripped2 = stripped.replace("{\"type\":\"xtracking\",\"xt\":\"21.","")
			stripped3 = stripped2.replace("}\"}","}")
			jsondata = json.loads(stripped3)
			id = str(jsondata['raw_id'])
			# sometimes the id comes back as None - ignore these
			if id != "None":
				link = element.find('a')['href']
				name_match = NameMatch(target.name, link, id)
				name_matches.append(name_match)
		except:
			continue

	return name_matches


# given a target photo, get the name and run an fb search
# from the fb results, run a face rec and return profiles that
# match above a given tolerance
def match_fb_target_to_potentials(target_photo:TargetPhoto, session:LoggedInSession,
							  dirs:Directories, optional_args="", tolerance=0.6):

	targets = convert_target_photo_to_targets(target_photo)

	# get the target encodings for everyone in the target photo
	target_image = face_recognition.load_image_file(target_photo.url)
	target_encodings = face_recognition.face_encodings(target_image)

	face_matches = []

	# keep a tally of the total number of name matches
	# a result of 0 might indicate that the login is borked
	total_name_matches = 0

	# so long as we find faces in the target photo:
	if len(target_encodings) > 0:

		# loop through each of the targets
		for target in targets:
			
			# scrape FB for possible profile matches
			name_matches = find_fb_name_matches(target, optional_args, session, "")

			# increase the name match count
			total_name_matches = total_name_matches + len(name_matches)

			# for each name match that we find:
			for name_match in name_matches:

				# us the FB social graph
				# note that this doesn't necessarily require a login...
				image_url = f"https://graph.facebook.com/{name_match.id}/picture?width=8000"

				# find the photo
				session.driver.get(image_url)
				img = session.driver.find_element_by_xpath("//img[1]")
				src = img.get_attribute('src')
				image_file = f"{dirs.temp_dir}/{name_match.id}.jpg"

				# download the photo and store in the temp directory
				urllib.request.urlretrieve(src, image_file)

				# get all the face encodings in the FB profile photo
				# as often there will be more than 1 face
				potential_match_image = face_recognition.load_image_file(image_file)

				potential_match_encodings = face_recognition.face_encodings(potential_match_image)

				# check for possible face matches
				for potential_match_encoding in potential_match_encodings:

					results = face_recognition.face_distance(target_encodings, 
											potential_match_encoding)

					# the result is the float euclidean distance between the
					# face vectors. The lower this is, the closer the match
					for result in results:

						if result < tolerance:

							print("found a potential match")

							name = f"{target.name}"

							found_match = FaceMatch(name,target_photo.url, 
							name_match.profile_link, result)

							face_matches.append(found_match)
				
				# Delete this line to keep the FB photos should you wish
				os.remove(image_file)

	# flag any case where the number of name matches was zero
	is_suspect = (total_name_matches == 0)
	move_completed_photo(target_photo, dirs, is_suspect)

	return face_matches


# -----------------------------------------------------------------------------
#
#	Instagram scraping and photo matching functions
#
# -----------------------------------------------------------------------------


# given a target, return the first page of search results
# from instagram. The optional_args are a string of space delimted extra terms
# to be appended to the search URL (i.e. "united kingdom")
# Returns a list of Potential Matches
def find_ig_name_matches(target:Target, optional_args:str, session:LoggedInSession):
	
	url = "https://www.instagram.com/"
	session.driver.get(url)
	sleep(3)
	try:
		#print("Closing \"Turn On Notifications\" message")
		self.driver.find_element_by_class_name("aOOlW").click()
		sleep(3)
	except:
		#print("Closing Message Failed or did not exist")
		pass
	
	searchbar = session.driver.find_element_by_xpath("//input[@placeholder='Search']")
	searchbar.send_keys(target.name)
	sleep(1)
	searchresponse = session.driver.page_source.encode('utf-8')
	sleep(1)
	soup = BeautifulSoup(searchresponse, 'html.parser')

	name_matches = []

	# search results are in a div with class=_401d
	for element in soup.find_all('div', {'class': '_401d'}):
		try:
			datagt = element['data-gt']
			stripped = datagt.replace("\\","")
			stripped2 = stripped.replace("{\"type\":\"xtracking\",\"xt\":\"21.","")
			stripped3 = stripped2.replace("}\"}","}")
			jsondata = json.loads(stripped3)
			id = str(jsondata['raw_id'])
			# sometimes the id comes back as None - ignore these
			if id != "None":
				link = element.find('a')['href']
				name_match = NameMatch(target.name, link, id)
				name_matches.append(name_match)
		except:
			continue
	
	for element in soupParser.find_all('a', {'class': 'yCE8d'}):
		
		try:
			link = "https://instagram.com" + element['href']
			profilepic = element.find('img')['src']

			name_match = NameMatch(target.name, link, profilepic)
			name_matches.append(name_match)

		except:
			#The find imgsrc fails on search items that arn't profiles so we catch and continue
			continue

	return name_matches


# given a target photo, get the name and run an fb search
# from the fb results, run a face rec and return profiles that
# match above a given tolerance
def match_ig_target_to_potentials(target_photo:TargetPhoto, session:LoggedInSession,
								dirs:Directories, optional_args="", tolerance=0.6):

	targets = convert_target_photo_to_targets(target_photo)

	# get the target encodings for everyone in the target photo
	target_image = face_recognition.load_image_file(target_photo.url)
	target_encodings = face_recognition.face_encodings(target_image)

	face_matches = []

	# keep a tally of the total number of name matches
	# a result of 0 might indicate that the login is borked
	total_name_matches = 0

	# so long as we find faces in the target photo:
	if len(target_encodings) > 0:

		# loop through each of the targets
		for target in targets:
			
			# scrape FB for possible profile matches
			name_matches = find_fb_name_matches(target, optional_args, session, "")

			# increase the name match count
			total_name_matches = total_name_matches + len(name_matches)

			# for each name match that we find:
			for name_match in name_matches:

				# us the FB social graph
				# note that this doesn't necessarily require a login...
				image_url = name_match.id

				# find the photo
				session.driver.get(image_url)
				img = session.driver.find_element_by_xpath("//img[1]")
				src = img.get_attribute('src')
				image_file = f"{dirs.temp_dir}/{name_match.id}.jpg"

				# download the photo and store in the temp directory
				urllib.request.urlretrieve(src, image_file)

				# get all the face encodings in the FB profile photo
				# as often there will be more than 1 face
				potential_match_image = face_recognition.load_image_file(image_file)

				potential_match_encodings = face_recognition.face_encodings(potential_match_image)

				# check for possible face matches
				for potential_match_encoding in potential_match_encodings:

					results = face_recognition.face_distance(target_encodings, 
											potential_match_encoding)

					# the result is the float euclidean distance between the
					# face vectors. The lower this is, the closer the match
					for result in results:

						if result < tolerance:

							print("found a potential match")

							name = f"{target.name}"

							found_match = FaceMatch(name,target_photo.url, 
							name_match.profile_link, result)

							face_matches.append(found_match)
				
				# Delete this line to keep the FB photos should you wish
				os.remove(image_file)

	# flag any case where the number of name matches was zero
	is_suspect = (total_name_matches == 0)
	move_completed_photo(target_photo, dirs, is_suspect)

	return face_matches






# -----------------------------------------------------------------------------
#
#	Operative routines
#
# -----------------------------------------------------------------------------


# csv file of email logins and passwords
# CHANGE THIS
LOGINS_FILE = "logins.csv"

# FB login page. Note this may also be http://www.facebook.com/login.php
#LOGIN_URL = "http://www.facebook.com"
LOGIN_URL = "https://www.instagram.com/accounts/login/?hl=en"

# root folder for the analysis
# note that this should have a sub-directory called unscanned, which is
# where the target photos should be stored
# CHANGE THIS
ROOT_DIR = ""

# this is the number of searches we will do for each login
NUM_PHOTOS_PER_SESSION = 100

# search may be improved for very common names by adding an optional
# search term such as "united kingdom" to narrow the list
OPTIONAL_ARGS = ""

# minimum face distance between target and FB photo in order for it to
# be considered a match
TOLERANCE = 0.6

# get the logins
logins = get_logins_from_file(LOGINS_FILE)

possible_matches = []

# set up the directory structure
dirs = Directories(ROOT_DIR)

# iterate over the logins sequentially
for login in logins:

	#session = try_log_into_fb_broswer_session(login, LOGIN_URL)
	session = try_log_into_ig_broswer_session(login, LOGIN_URL)

	if session is FailedLogin:
		print(f"Failed to login for {login.login_email}")

	else:

		# get a list of target photos of length NUM_PHOTOS_PER_SESSION
		target_photos = stage_target_photos(dirs, NUM_PHOTOS_PER_SESSION)

		file = f"{ROOT_DIR}/{session.login_email}.csv"

		with open(file, 'a', newline='') as output_file:

			writer = csv.writer(output_file)

			try:

				for target_photo in target_photos:

					# get the face matches for each target photo
					#face_matches = match_fb_target_to_potentials(target_photo, session, dirs)
					face_matches = match_ig_target_to_potentials(target_photo, session, dirs)

					if len(face_matches) == 0:

						msg = f"No matches for {target_photo.url}"

						writer.writerow([msg])

						output_file.flush()

						print(msg)

					for face_match in face_matches:

						possible_matches.append(face_match)

						msg = f"{face_match.target_name} | {face_match.match_profile} | {face_match.dist}"

						writer.writerow([face_match.target_name, face_match.match_profile, face_match.dist ])

						output_file.flush()

						print(msg)

			except:

				msg = f"Error encountered for {session.login_email}"

				writer.writerow([msg])

				print(msg)

				continue

		# for any complete login session, unstage any photos which are still staged
		unstage_target_photos(dirs, target_photos)

				
