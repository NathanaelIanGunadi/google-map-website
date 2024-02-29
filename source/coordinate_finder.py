import requests

def get_lat_lng(address):
    base_url = "https://nominatim.openstreetmap.org/search"

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    params = {
        'q': address,
        'format': 'json',
    }

    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        results = response.json()
        if results:
            return (float(results[0]['lat']), float(results[0]['lon']))
        else:
            return None
    else:
        raise Exception(f"Error: {response.status_code}")

def main():
    address = "町田駅"

    lat_lng = get_lat_lng(address)
    if lat_lng:
        print(f"Latitude: {lat_lng[0]}, Longitude: {lat_lng[1]}")
    else:
        print("Location not found.")

if __name__ == "__main__":
    main()
