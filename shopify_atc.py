'''
@author: yung_messiah

'''
import requests
import bs4
import re


headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}

''' Retrieves sizes for item in stock.

    @param url: The url passed by the user pointing to the item he/she wants ''' 
def get_sizes(url):
    # Ensure url starts with https:// in case url only contains www....
    url_formatting = re.match('https://', url)
    if url_formatting == None:
        url = 'https://' + url
    try:
        raw_HTML = requests.get(url, headers=headers, timeout=5)
        if raw_HTML.status_code != 200:
            print("An error has occured completing your request")
            return False
        else:
            page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
            print(page.title.string)
            status = get_size_variant(url, page)
            return status
    except requests.Timeout as error:
        print("There was a timeout error")
        print(str(error))
    except requests.ConnectionError as error:
        print("A connection error has occured. The details are below.\n")
        print(str(error))
    except requests.RequestException as error:
        print("An error occured making the internet request.")
        print(str(error))
        
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
    
''' Retrieves the thumbnail image for the item requested.
    
    @param page: HTML containing information to be scraped for image URL '''
def get_thumbnail_image(page):
    correct_image = None
    img = page.find_all('img')
    for i in img:
        if 'products' in str(i):
            correct_image = str(i)
            break
    
    if correct_image == None:
        print(None)
    else:
        item_image_url = re.search('cdn\.shopify.+\"', correct_image)
        if item_image_url == None:
            print("REGEX RETURNED NONE")
        else:
            item_image_url = item_image_url.group()
            item_image_url = item_image_url.split(' ')
            url = "https://"
            url += item_image_url[0].replace('"','')
            print(url)
        
                  

    
''' Retrieves the id associated to the item size (required to create a link). 

    @param url: The item's url  
    @param page: Page information retrieved through requests '''
def get_size_variant(url, page):
    scripts = page.find_all("script")
    if scripts == None:
        print("An error has occured completing your request")
        return False
    
    script_index = find_variant_script(scripts)
    
    script = scripts[script_index].getText()
    get_thumbnail_image(page)
    
    
    ''' split it in this manner to store items of script separated by a new line '''
    script = script.split(';')
    ''' retrieve only the line containing size information '''
    script = script[3]
    ''' split in this manner so that each size is a different list item '''
    script = script.split('{\"id\":')
    ''' remove unwanted information in beginning of list '''
    script.remove(script[0])
    script.remove(script[0])
    
    status = True  
    for item in script:
        if 'public_title\":\"' in item:
            data = item
            data = data.split(',')
            
            size = data[3].split("\"")
            size = size[3]
            print(size)
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
            status = print_link(url, item_size, str(retrieved_id))
            if status == False:
                break
            
    return status


''' Prints a correctly formated link which takes user straight to purchase.

    @param url: URL of the item to be bought
    @param size: Size of the given item
    @param retrieved_id: Id associated to the item size  '''
def print_link(url, size, retrieved_id):
    absolute_url = get_absolute_url(url)
    if absolute_url == False:
        print("An error has occured completing your request")
        return False

    print('[ ' + size +  ' ] \t[ ATC ](', absolute_url + 'cart/' + retrieved_id + ':1)')
    return True

''' Kickstarts the entire script.

    @param url: The url pointing to the item which the user wants to buy '''
def run(url):
    status = get_sizes(url)
    
    return status
    
def find_variant_script(scripts):  
    ''' Loops through all the scripts on page to find correct script containing size data 
            We uncomment the code below if we get errors in the future retrieving data from 
            the page
    '''
    for number, script in enumerate(scripts):
        if "variants\":[{" in script.getText():
            return number
            break
        
def check_if_shopify(url):
    # Ensure url starts with https:// in case url only contains www....
    url_formatting = re.match('https://', url)
    if url_formatting == None:
        url = 'https://' + url
    
    print(url)
    try:
        raw_HTML = requests.get(url, headers=headers, timeout=5)
        if raw_HTML.status_code != 200:
            print("An error has occured completing your request")
            return False
        else:
            page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
            script = page.find_all('script')
            for i in script:
                if 'shopify' in str(i).lower():
                    print(str(i))
                    return True
            return False
    except requests.Timeout as error:
        print("There was a timeout error")
        print(str(error))
    except requests.ConnectionError as error:
        print("A connection error has occured. Make sure you are connected to the Internet. The details are below.\n")
        print(str(error))
    except requests.RequestException as error:
        print("An error occured making the internet request.")
        print(str(error))
            

check_if_shopify("www.kith.com")