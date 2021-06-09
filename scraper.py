import urllib.request
import csv
import requests
import shutil
import pathlib
import os
from bs4 import BeautifulSoup

OUTPUT_DIRECTORY = "C:/Users/CJW/Test/unscanned"

# helper function - returns a BeautifulSoup object
# for a given URL
def get_soup(url):

    html = urllib.request.urlopen(url)

    soup = BeautifulSoup(html, 'html.parser')

    return soup


# main function - for a given region
# extracts the paedos and photo url into a CSV file
# and then saves each photo with the paedo name
# for each region the function will start on the first page, then
# recursively call itself with an incrementing page number
# until it fails to find an "Older Posts" button on the page
def paedocapture(region, page_num=1):


    url = f"https://theukdatabase.net/category/{region}/"

    if page_num != 1:
        url = f"https://theukdatabase.net/category/{region}/page/{page_num}/"

    # paedos are linked in the region page by an element that
    # includes a rel=bookmark tag
    paedorefs = get_soup(url).find_all('a', attrs={'rel': 'bookmark'})

    paedos = []

    # make list of paedo links
    for ref in paedorefs:
        paedoname = ref.text.strip()
        paedolink = ref.attrs['href']
        paedos.append((paedoname, paedolink))

    paedodata = []

    # from each paedo link, get the photo url
    # helpfully included in the meta data on each page
    for paedoname, paedolink in paedos:

        paedomug = get_soup(paedolink).find('meta', attrs={'property': 'og:image'}).attrs['content']
        paedodata.append((paedoname, paedomug))


    # output csv file
    file = f"{OUTPUT_DIRECTORY}/{region}({page_num}).csv"

    # write name & photo link to csv for the region
    # newline param needed as python is retarded and will
    # insert a blank line between every record otherwise
    with open(file, 'a', newline='') as csv_file:

        writer = csv.writer(csv_file)

        # rename and save the photos
        for paedoname, paedomug in paedodata:

            try:

                # for pages with no photo, the meta link is always
                # blank.jpg, so filter this out
                if paedomug != "https://s0.wp.com/i/blank.jpg":
                    
                    # download photo
                    resp = requests.get(paedomug, stream=True)

                    # get the photo filename and file extension
                    photourl = os.path.basename(paedomug)
                    extension = pathlib.Path(photourl).suffix

                    # remove the region name in the paedo name (delimited with a " - ")
                    # and replace any slashes for multiple parties with ampersand
                    localfilename = paedoname.split(" – ")[0].replace("/", " & ")

                    # file name for local photo with correct extension
                    # TODO: convert png to jpg with the PIL library?
                    localmug = open(f"{OUTPUT_DIRECTORY}/{localfilename}{extension}", 'wb')

                    resp.raw.decode_content = True

                    # copy the downloaded photo to the local file
                    shutil.copyfileobj(resp.raw, localmug)

                    # delete the downloaded photo so the temp file isn't filled with
                    # photos of paedos
                    del resp

                    writer.writerow([paedoname, paedomug])

            except:
                # some photos seem to have invalid urls, generally those offsite from the main db
                writer.writerow([f"Error for {paedoname} - {paedomug}"])
                

    # is there an "Older Posts" button on the page?
    # (note that nav-previous div exists even when there are no older posts
    # only the text is left blank. Oh the shitness of Wordpress.)
    has_older_posts = get_soup(url).find('div', attrs={'class': 'nav-previous'})

    # if so, then increment the page number and call the function recursively
    if has_older_posts is not None:
        if has_older_posts.text != "":
            next_page_num = page_num + 1
            paedocapture(region, next_page_num)




# All regions on the website
regions = ['Aberdeenshire',
'All-Areas',
'Angus',
'Animal-perverts',
'Argyll',
'Avon-and-Somerset-Bristol',
'Ayrshire',
'Bail-Hostel',
'Banffshire',
'Bedfordshire',
'Berkshire',
'Berwickshire',
"Boys-Brigade",
'Buckinghamshire',
'Caerphilly',
'Cambridgeshire',
'Carmarthenshire',
'Ceredigion',
'Cheshire',
'Child-Killer',
'Childrens-homes-Boarding-schools',
'Clackmannanshire',
'Clergymen',
'Clwyd',
'Company-Director-Owner',
'Conwy',
'Cornwall',
'Councillor-Political-party',
'Cumbria',
'Denbighshire',
'Deported',
'Derbyshire',
'Devon',
'Doctors-Nurses',
'Dorset',
'Dumfries-Galloway',
'Dunbartonshire',
'Durham',
'Dyfed-Powys',
'East-Yorkshire',
'Edinburgh',
'Essex',
'Female-Abuser',
'Fife',
'Flintshire',
'Foster-Carers',
'Glamorgan',
'Glasgow',
'Gloucestershire',
'Greater-Manchester',
'Guernsey',
'Gwent',
'Gwynedd',
'Hampshire',
'Hebrides-islands',
'Herefordshire',
'Hertfordshire',
'Highlands',
'Humberside',
'HuntingTeam',
'Inverness-shire',
'Isle-Of-Anglesey',
'Isle-of-Bute',
'Isle-of-Lewis',
'Isle-of-man',
'Isle-of-Wight',
"Jehovahs-Witnesses",
'Jersey',
'Judge/Magistrate',
'Justice-for-campaigns',
'Kent',
'Lanarkshire',
'Lancashire',
'Leicestershire',
'Lincolnshire',
'Location-not-reported',
'London',
'Lothian',
'Lowlands',
'Merseyside',
'Middlesex',
'Midlothian',
'Monmouthshire',
'Morayshire',
'N-Ireland',
'N-Yorks-Cleveland-Middlesborough',
'Neath',
'Norfolk',
'North-Wales',
'Northamptonshire',
'Northumberland',
'Nottinghamshire',
'Nursery-Worker',
'Operation-Spade',
'Orkney',
'Outer-Hebrides',
'Overseas-Linked-to-UK',
'Oxfordshire',
'Pembrokeshire',
'Perthshire',
'Police',
'Police-sting',
'Renfrewshire',
'Republic-of-Eire',
'Revenge-porn-against-adults',
'Rhondda-Cynon-Taf',
'Ross-Shire',
'Scottish-Borders',
'Scout-groups',
'Serial-child-killers',
'Shetland',
'Shropshire',
'Social-Network-Internet-Predators',
'Social-worker',
'South-Wales',
'South-Yorkshire',
'Staffordshire',
'Statistics',
'Stirlingshire',
'Stockton-on-Tees',
'Suffolk',
'Surrey',
'Sussex',
'Teacher',
'Too-Lenient-Sentences',
'Torfaen',
'Tyne-and-Wear',
'UK-paedophile-ring',
'Uncategorized',
'Warwickshire',
'West-Midlands',
'West-yorkshire',
'Wiltshire',
'Worcestershire',
]

# downloads a single region
paedocapture('Avon-and-Somerset-Bristol')

# uncomment the code below to run all regions

# for region in regions:
#     try:
#         paedocapture(region)
#     except Exception as e:
#         str_error = str(e)
#         print(f"Error encountered for {region}: {str_error}")
#         continue
