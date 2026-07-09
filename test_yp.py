import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

url = 'https://www.yellowpages.com/search?search_terms=plumber&geo_location_terms=Raleigh%2C+NC'
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"YellowPages Status: {r.status_code}, Length: {len(r.text)}")
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # YellowPages organic listings are in divs with class "organic" or similar, or containing class "v-card"
    cards = soup.find_all(class_='v-card')
    print(f"Total v-card listing blocks found: {len(cards)}")
    for i, c in enumerate(cards[:5]):
        name_tag = c.find(class_='business-name')
        name = name_tag.text.strip() if name_tag else "Unknown"
        
        # Phone
        phone_tag = c.find(class_='phone')
        phone = phone_tag.text.strip() if phone_tag else "Unknown"
        
        # Website
        track_tag = c.find(class_='track-visit-website')
        web = track_tag['href'] if track_tag and track_tag.has_attr('href') else "Unknown"
        
        print(f"{i+1}. Name: {name} | Phone: {phone} | Web: {web}")
except Exception as e:
    print(f"Error: {e}")
