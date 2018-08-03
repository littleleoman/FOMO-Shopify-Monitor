'''
@author: yung_messiah

'''
import bs4
import discord
import os
import pymongo
import re
import requests

from discord.embeds import Embed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry

discord_client = None
db = None
shopify = None

MONGODB_URI = os.environ['MONGODB_URI']

HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
WEBSITES = ['www.12amrun.com','www.18montrose.com','www.a-ma-maniere.com','www.abovethecloudsstore.com','www.addictmiami.com',
                'www.apbstore.com','www.bbbranded.com','www.bbcicecream.com','www.blendsus.com','www.blkmkt.us',
                'www.bowsandarrowsberkeley.com','www.capsuletoronto.com','www.cityblueshop.com','www.clot.com','www.cncpts.com',
                'www.cntrbndshop.com','www.commonwealth-ftgg.com','www.deadstock.ca','www.dope-factory.com','shop.exclucitylife.com',
                'shop.extrabutterny.com','www.fearofgod.com','www.featuresneakerboutique.com','www.ficegallery.com','www.hanon-shop.com',
                'www.havenshop.com','www.highsandlows.net.au','www.kongonline.co.uk','www.laceupnyc.com','www.lapstoneandhammer.com',
                'www.leaders1354.com','www.minishopmadrid.com','www.notre-shop.com','www.nrml.ca','us.octobersveryown.com',
                'www.offthehook.ca','www.oipolloi.com','www.oneness287.com','www.philipbrownemenswear.co.uk','www.properlbc.com',
                'www.renarts.com','www.rimenyc.com','www.rise45.com','www.rockcitykicks.com','www.rsvpgallery.com',
                'www.saintalfred.com','www.shoegallerymiami.com','www.shopnicekicks.com','www.sneakerpolitics.com','www.sneakerworldshop.com',
                'www.socialstatuspgh.com','www.soleclassics.com','www.solefly.com','www.stampd.com','www.suede-store.com',
                'www.theclosetinc.com','www.thedarksideinitiative.com','www.thepremierstore.com','www.thesportsedit.com','shop.travisscott.com',
                'www.trophyroomstore.com','www.undefeated.com','www.urbanindustry.co.uk','www.vlone.co','www.westnyc.com',
                'www.wishatl.com','www.worldofhombre.com','www.xhibition.co']

KEYWORDS = ['Butter','Blue Tint', 'Beluga', 'Semi Frozen Yellow', '350 V2 Zebra',
            '350 V2 Cream White', '500 Blush', ' 500 Super Moon Yellow', '500 Utility Black', 
            'Wave Runner 700', 'Pharrell Holi', 'Pharrell Oreo', 'Pharrell Multi-Color',
            'Pharrell Sun Glow', 'Pharrell Blank Canvas','Jordan 1', 'NRG', 'Air Max 90',
            'Air VaporMax', 'Air Presto', 'Air Force 1 Low', 'Air Max 97', 'Converse Chuck Taylor',
            'Hyperdunk Flyknit','Nike Zoom Fly', 'Nike Blazer Mid', 'Zoom Fly Mercurial', 'Jordan 4 Retro Levi',
            'Jordan 4 Retro Travis Scott', 'Jordan 4 Retro Cactus Jack', 'Air Max 1/97 Sean Wotherspoon', 
            'Air Max 1/97 Wotherspoon', 'Jordan 3 Retro Tinker Hatfield', 'React Element 87']


def request_with_retry(retries=4, backoff_factor=0.2, session=None, status_forcelist=(500, 503, 504, 400, 403, 404, 408)):
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    session = session or requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter) 
    return session

''' Retrieves only the absolute URL from passed in URL.
  
@param url: The address passed in by the user '''    
def get_absolute_url(url):
    absolute_url = re.match('https://', url)
    if absolute_url == None:
        absolute_url = re.match('[a-zA-Z0-9.-]+/', url)
        if absolute_url == None:
            return False
        absolute_url = absolute_url.group()
        return absolute_url
    else:
        absolute_url = re.match('https://[a-zA-Z0-9.-]+/', url)
        absolute_url = absolute_url.group()
        return absolute_url


class Product(object):
    
    def __init__(self, name, sizes, variant_ids, image_url, website_url):
        self.name = name
        self.sizes = sizes
        self.variant_ids = variant_ids
        self.image_url = image_url
        self.website_url = website_url
        self.insert_data()
        
    def insert_data(self):
        # Create seed data
        item = [
            {
                'item': self.name,
                'sizes': sizes,
                'variant_ids': variant_ids,
                'image_url': image_url,
                'website': website_url 
            }
        ]
        
        shopify.insert_one(item)
    
class ItemObserver(object):
    def __init__(self):
        for site in WEBSITES:
            site += "/sitemap_products_1.xml"
            ObserverSitemapScraper(site)


class DiscordManager(object):
    async def post(product):
        desc = "[" + product.website_url + "](" + product.website_url + ")"
        
        embed = Embed(title=product.name, description=desc, color=0x008f00)
        embed.add_field(name="Sizes", value=product.sizes)
        embed.add_field(name="ATC", value=product.atc_links)
        # TODO - ADD A DESTINATION!
        await client.send_message(embed=embed)
        

##############################################################
#                                                            #
#               Constant Site Monitoring                     #
#                                                            #
############################################################## 
class ObserverSitemapScraper(object):
    def __init__(self, url):
        self.page = None
        self.url = url
        self.item_urls = []
        self.last_modified = []
        self.image_urls = []
        self.item_names = []
        self.absolute_url = get_absolute_url(self.url)
        
        self.scrape()
    
    
    def scrape(self):
        # Ensure url starts with https:// in case url only contains www....
        url_formatting = re.match('https://', self.url)
        if url_formatting == None:
            self.url = 'https://' + self.url
        try:
            raw_HTML = request_with_retry().get(self.url, headers=HEADERS, verify=False, timeout=5)
            if raw_HTML.status_code != 200:
                print("An error has occured completing your request")
                return False
            else:
                page = bs4.BeautifulSoup(raw_HTML.text, 'xml')
#                 print(page.title.string)
                self.page = page
                self.get_structure()
#                 self.get_item_urls()
        except requests.Timeout as error:
            print("There was a timeout error")
            print(str(error))
        except requests.ConnectionError as error:
            print("A connection error has occured. The details are below.\n")
            print(str(error))
        except requests.RequestException as error:
            print("An error occured making the internet request.")
            print(str(error))
    
    def get_structure(self):
        structure = self.page.find_all("url")
        del structure[0]
        for item in structure:
            name = re.search('<image:title>(.*)</image:title>', str(item))
            if name == None:
                continue
            else:
                name = name.group(1)
                for keyword in KEYWORDS[1:26]:
                    if keyword.lower() in name.lower().replace('"','') and 'yeezy' in name.lower():
                        print("Yeezy " + keyword, str(self.url))
                        self.verify_in_database(item, name, self.absolute_url)
                    elif keyword.lower() in name.lower().replace('"','') and 'nmd' in name.lower():
                        print("NMD " + keyword, str(self.url))
                        self.verify_in_database(item, name, self.absolute_url)
                    elif keyword.lower() in name.lower().replace('"','') and ('off white' in name.lower().replace('-', ' ') or ('offwhite') in name.lower()):
                        print("Off-White " + keyword, str(self.url))
                        self.verify_in_database(item, name, self.absolute_url)
                for keyword in KEYWORDS[26:]:
                    if keyword.lower() in name.lower().replace('"',''):
                        print(keyword, str(self.url))
                        self.verify_in_database(item, name, self.absolute_url)
        
        self.format_product()
                        
                        
    def retrieve_full_item_data(self, item):
        item_url = re.search('<loc>(.*)</loc>', str(item))
        if item_url == None:
            self.item_urls.append('N/A')
        else:
            self.item_urls.append(item_url.group(1))
                
        date = re.search('<lastmod>(.*)</lastmod>', str(item))
        if date == None:
            self.last_modified.append('N/A')
        else:
            self.last_modified.append(date.group(1))
                
        image = re.search('<image:loc>(.*)</image:loc>', str(item))
        if image == None:
            self.image_urls.append('N/A')
        else:
            self.image_urls.append(date.group(1))
                
        name = re.search('<image:title>(.*)</image:title>', str(item))
        if name == None:
            self.item_names.append('N/A')
        else:
            self.item_names.append(name.group(1))
                    
                    
            
    def verify_in_database(self, item, name, url):
        # check if this item is on the database
        # if it is: Check if the last modified is more recent
        # than the data in the database
        cursor = shopify.find_one({'item': name, 'site': url})
        if cursor == None:
            self.retrieve_full_item_data(item)
        else:
            for doc in cursor:
                print('Name: %s, Image: %s' % doc['item'], doc['image_url'])
                
    
    def format_product(self):
        for index,url in enumerate(self.item_urls):
            item = DatabaseItemScraper(url)
            Product(self.item_names[index], item.sizes, item.retrieved_ids, self.image_urls[index], item.absolute_url)


class DatabaseItemScraper(object):
    
    def __init__(self, url):
        self.page = None
        self.url = url
        self.sizes = []
        self.retrieved_ids = []
        self.absolute_url = get_absolute_url(url)
        self.get_sizes(self.url)
    
    ''' Retrieves sizes for item in stock.

    @param url: The url passed by the user pointing to the item he/she wants ''' 
    def get_sizes(self, url):
        # Ensure url starts with https:// in case url only contains www....
        url_formatting = re.match('https://', url)
        if url_formatting == None:
            self.url = 'https://' + url
        try:
            raw_HTML = requests.get(self.url, headers=HEADERS, timeout=5)
            if raw_HTML.status_code != 200:
                print("An error has occured completing your request")
                return False
            else:
                page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
#                 print(page.title.string)
                self.page = page
                self.get_size_variant()
        except requests.Timeout as error:
            print("There was a timeout error")
            print(str(error))
        except requests.ConnectionError as error:
            print("A connection error has occured. The details are below.\n")
            print(str(error))
        except requests.RequestException as error:
            print("An error occured making the internet request.")
            print(str(error))
            
    ''' Retrieves the id associated to the item size (required to create a link). 

    @param url: The item's url  
    @param page: Page information retrieved through requests '''
    def get_size_variant(self):
        scripts = self.page.find_all("script")
        if scripts == None:
            print("An error has occured completing your request")
            return False
        
        
        script_index = self.find_variant_script(scripts)
        script_index = script_index.split(':')
        script = scripts[int(script_index[1])].getText()
        if script_index[0] == 'variant':
            ''' split it in this manner to store items of script separated by a new line '''
            script = script.split(';')
            ''' retrieve only the line containing size information '''
            script = script[3]
            ''' split in this manner so that each size is a different list item '''
            script = script.split('{\"id\":')
            ''' remove unwanted information in beginning of list '''
            script.remove(script[0])
            script.remove(script[0])
            
            for item in script:
                if 'public_title\":\"' in item:
                    data = item
                    data = data.split(',')
                    
                    size = data[3].split("\"")
                    size = size[3]
                    retrieved_id = data[0]
                    
                    # add leading and trailing spaces to make regex matching easier
                    size = " " + size + " "
                    item_size = re.search('\s\d+\.\d+\s', str(size))
                    if item_size == None:
                        item_size = re.search('\s\d{1,2}\s', str(size))
                        if item_size == None:
                            item_size = re.search('(?i)(XS|X-S|(\sS\s|Small)|(\sM\s|Medium)|(\sL\s|Large)' + 
                                                          '|XL|XXL|XXXL|X-L|XX-L|XXX-L)', str(size))
                            if item_size == None:
                                item_size = size
                    
                    if item_size != size:
                        item_size = item_size.group()
                        
                    item_size = item_size.replace('\\', '')
                    item_size = item_size.replace('/', "")
                    item_size += '//0'
                    self.save_data(item_size, str(retrieved_id))
        else:
    #         ''' split it in this manner to store items of script separated by a new line '''
    #         script = script.split(';')
            ''' split in this manner so that each size is a different list item '''
            script = script.split('{\"id\":')
    
            ''' remove unwanted information in beginning of list '''
            script.remove(script[0])
            script.remove(script[0])
    #         
            for item in script:
                data = re.search('(.*),"title.*public_title":"(.*)","options.*inventory_quantity":(.*),"inventory_management', str(item))
                retrieved_id = data.group(1)
                item_info = data.group(2) + '//' + data.group(3)
                self.save_data(item_info, str(retrieved_id))


    def find_variant_script(self, scripts):  
        ''' Loops through all the scripts on page to find correct script containing size data 
                We uncomment the code below if we get errors in the future retrieving data from 
                the page
        '''
        index = None
        
        for number, script in enumerate(scripts):
            if "inventory_quantity" in script.getText():
                index = 'quantity:' + str(number)
                break
        
        if index == None:
            for number, script in enumerate(scripts):
                if "variants\":[{" in script.getText():
                    index = 'variant:' + str(number)
                    break
        
        return index
            
    '''Correctly stores size data to Scraper object.

    @param size: Size of the given item
    @param retrieved_id: Id associated to the item size  '''
    def save_data(self, info, retrieved_id):
        self.sizes.append(str(info))
        self.retrieved_ids.append(str(retrieved_id))
        

if __name__ == "__main__":
#     discord_client = discord.Client()
    db_client = pymongo.MongoClient(MONGODB_URI,
                                    connectTimeoutMS=30000,
                                    socketTimeoutMS=None,
                                    socketKeepAlive=True)
    db = db_client.get_default_database()
    shopify = db['shopify']
    shopify.create_index('website')
    
    ItemObserver()
    
    db_client.close()

