import requests
import json
from source.coordinate_finder import get_lat_lng
from collections import defaultdict
import math


class GoogleMapScraper:

    def __init__(self, keywords, location, radius, api_key, sorting=0):
        self.sort_methods = ["rating", "price_level", "user_ratings_total", "vicinity"]
        self.categories = ("rating", "price_level", "user_ratings_total", "vicinity", "geometry")
        self.sorting = self.sort_methods[sorting]
        self.keywords = keywords
        self.location = location
        self.radius = radius
        self.api_key = api_key
        self.targets_dict = defaultdict(dict)

    def search_places(self, api_key, keyword, location, radius):
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        self.lat_lng = get_lat_lng(location)
        try:
            location_coords = ",".join([str(x) for x in self.lat_lng])
        except TypeError:
            return False

        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        params = {
            'key': api_key,
            'keyword': keyword,
            'location': location_coords,
            'radius': radius,
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error: {response.status_code}")

    def run(self):
        for keyword in self.keywords:
            result = self.search_places(self.api_key, keyword, self.location, self.radius)
            if not result:
                return False

            targets = result.get('results', [])

            for target in targets:
                if not target.get('permanently_closed', False):
                    for category in self.categories:
                        if category == "price_level":
                            if target.get(category) is None:
                                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")][category] = "-"
                            else:
                                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")][category] = str(target.get(category))
                        elif category == "geometry":
                            self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")]["lat"] = target.get(category).get("location").get("lat")
                            self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")]["lng"] = target.get(category).get("location").get("lng")
                            lat1 = self.lat_lng[0] / (180 / math.pi)
                            lng1 = self.lat_lng[1] / (180 / math.pi)
                            lat2 = target.get(category).get("location").get("lat") / (180 / math.pi)
                            lng2 = target.get(category).get("location").get("lng") / (180 / math.pi)
                            distance = math.acos((math.sin(lat1) *
                                      math.sin(lat2)) + math.cos(lat1) *
                                      math.cos(lat2) *
                                      math.cos(lng2 - lng1)) * 6371
                            self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")]["distance"] = round(distance, 2)
                        else:
                            try:
                                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")][category] = target.get(category).encode("utf-8").decode("utf-8")
                            except AttributeError:
                                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")][category] = target.get(category)

                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")]["type_of_place"] = keyword
                self.targets_dict[target.get("name").encode("utf-8").decode("utf-8")]["origin"] = self.location

        return True

if __name__ == "__main__":
    a = GoogleMapScraper(["restaurant"], "町田駅", 10, "AIzaSyDbbDAUExwpzu7IaZ1h_Xw5-i6P2jwtXXs")
    a.run()
