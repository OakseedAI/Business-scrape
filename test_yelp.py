import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

url = 'https://www.yelp.com/search?find_desc=plumbers&find_loc=Raleigh%2C+NC'
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Yelp Status: {r.status_code}, Length: {len(r.text)}")
    print(r.text[:500])
except Exception as e:
    print(f"Error: {e}")
